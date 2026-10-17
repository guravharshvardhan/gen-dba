import os
import time
import hmac
import hashlib
import base64
import json
import secrets

import psycopg2
from dotenv import load_dotenv

from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends


load_dotenv("backend/.env")


# =========================================================
# SECURITY CONFIG
# =========================================================

TOKEN_EXPIRY_SECONDS = 8 * 60 * 60

security = HTTPBearer()


def get_auth_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120000
    )

    return (
        base64.b64encode(salt).decode()
        + ":"
        + base64.b64encode(password_hash).decode()
    )


def verify_password(password, stored_hash):

    try:

        salt_b64, hash_b64 = stored_hash.split(":")

        salt = base64.b64decode(
            salt_b64
        )

        expected_hash = base64.b64decode(
            hash_b64
        )

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            120000
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except Exception:

        return False


# =========================================================
# DEFAULT USER SETUP
# =========================================================

def ensure_default_users():

    users = [
        {
            "username": os.getenv(
                "GENDBA_ADMIN_USERNAME",
                "admin"
            ),
            "password": os.getenv(
                "GENDBA_ADMIN_PASSWORD",
                "admin123"
            ),
            "role": "ADMIN"
        },
        {
            "username": os.getenv(
                "GENDBA_DBA_USERNAME",
                "dba"
            ),
            "password": os.getenv(
                "GENDBA_DBA_PASSWORD",
                "dba123"
            ),
            "role": "DBA"
        },
        {
            "username": os.getenv(
                "GENDBA_VIEWER_USERNAME",
                "viewer"
            ),
            "password": os.getenv(
                "GENDBA_VIEWER_PASSWORD",
                "viewer123"
            ),
            "role": "VIEWER"
        }
    ]

    conn = get_auth_connection()
    cursor = conn.cursor()

    try:

        for user in users:

            cursor.execute(
                """
                SELECT user_id
                FROM auth_users
                WHERE username = %s
                """,
                (user["username"],)
            )

            existing = cursor.fetchone()

            if not existing:

                password_hash = hash_password(
                    user["password"]
                )

                cursor.execute(
                    """
                    INSERT INTO auth_users
                    (
                        username,
                        password_hash,
                        role
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        user["username"],
                        password_hash,
                        user["role"]
                    )
                )

        conn.commit()

    finally:

        cursor.close()
        conn.close()


# =========================================================
# TOKEN
# =========================================================

def create_token(
    user_id,
    username,
    role
):

    secret = os.getenv(
        "GENDBA_JWT_SECRET"
    )

    if not secret:

        raise RuntimeError(
            "GENDBA_JWT_SECRET is missing in .env"
        )

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(
            time.time()
            + TOKEN_EXPIRY_SECONDS
        )
    }

    payload_json = json.dumps(
        payload,
        separators=(",", ":")
    ).encode()

    payload_b64 = base64.urlsafe_b64encode(
        payload_json
    ).decode()

    signature = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()

    signature_b64 = (
        base64.urlsafe_b64encode(
            signature
        ).decode()
    )

    return (
        payload_b64
        + "."
        + signature_b64
    )


def decode_token(token):

    secret = os.getenv(
        "GENDBA_JWT_SECRET"
    )

    if not secret:

        raise HTTPException(
            status_code=500,
            detail="Authentication secret is not configured."
        )

    try:

        payload_b64, signature_b64 = (
            token.split(".")
        )

        expected_signature = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()

        actual_signature = (
            base64.urlsafe_b64decode(
                signature_b64
            )
        )

        if not hmac.compare_digest(
            expected_signature,
            actual_signature
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token."
            )

        payload = json.loads(
            base64.urlsafe_b64decode(
                payload_b64
            ).decode()
        )

        if payload["exp"] < int(
            time.time()
        ):

            raise HTTPException(
                status_code=401,
                detail="Authentication token expired."
            )

        return payload

    except HTTPException:

        raise

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token."
        )


# =========================================================
# LOGIN
# =========================================================

def login_user(
    username,
    password
):

    conn = get_auth_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                role,
                is_active
            FROM auth_users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        user_id = user[0]
        db_username = user[1]
        password_hash = user[2]
        role = user[3]
        is_active = user[4]

        if not is_active:

            raise HTTPException(
                status_code=403,
                detail="User account is disabled."
            )

        if not verify_password(
            password,
            password_hash
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        token = create_token(
            user_id,
            db_username,
            role
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": user_id,
                "username": db_username,
                "role": role
            }
        }

    finally:

        cursor.close()
        conn.close()


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials =
        Depends(security)
):

    return decode_token(
        credentials.credentials
    )


# =========================================================
# ROLE CHECK
# =========================================================

def require_roles(*allowed_roles):

    def checker(
        current_user=Depends(
            get_current_user
        )
    ):

        role = current_user.get(
            "role"
        )

        if role not in allowed_roles:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Access denied for this role."
                )
            )

        return current_user

    return checker