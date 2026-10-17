import os
import time
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GenStore API", version="1.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5174",
#         "http://127.0.0.1:5174",
#         "http://10.25.180.220:5174",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://10.25.180.220:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "gendba"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


# def log_query(query_text: str, execution_time_ms: float):
#     """Log a real GenStore SQL request so Gen-DBA can observe the workload."""
#     conn = None
#     cursor = None
#     try:
#         conn = get_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             """
#             INSERT INTO query_logs
#             (query_text, execution_time, frequency, risk_score, impact_score)
#             VALUES (%s, %s, 1, 0, 0)
#             """,
#             (query_text, round(execution_time_ms, 3)),
#         )
#         conn.commit()
#     except Exception:
#         if conn:
#             conn.rollback()
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()
def log_query(
    query_text: str,
    execution_time_ms: float,
    search_term: Optional[str] = None
):
    """Log a GenStore SQL request for Gen-DBA workload tracking."""
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO query_logs
                (query_text, execution_time, frequency,
                 risk_score, impact_score, search_term)
            VALUES (%s, %s, 1, 0, 0, %s)
            """,
            (
                query_text,
                round(execution_time_ms, 3),
                search_term
            )
        )
        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Query logging failed: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# def fetch_all(query: str, params=None):
#     started = time.perf_counter()
#     conn = get_connection()
#     cursor = conn.cursor(cursor_factory=RealDictCursor)
#     try:
#         cursor.execute(query, params or ())
#         rows = cursor.fetchall()
#         elapsed = (time.perf_counter() - started) * 1000
#         return rows, elapsed
#     finally:
#         cursor.close()
#         conn.close()
#         log_query(query, (time.perf_counter() - started) * 1000)

def fetch_all(
    query: str,
    params=None,
    search_term: Optional[str] = None
):
    started = time.perf_counter()
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        elapsed = (time.perf_counter() - started) * 1000
        return rows, elapsed

    finally:
        elapsed = (time.perf_counter() - started) * 1000
        cursor.close()
        conn.close()
        log_query(query, elapsed, search_term)

def fetch_one(query: str, params=None):
    started = time.perf_counter()
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        return row, (time.perf_counter() - started) * 1000
    finally:
        cursor.close()
        conn.close()
        log_query(query, (time.perf_counter() - started) * 1000)


class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=20)


class OrderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    city: str = Field(min_length=2, max_length=100)
    items: list[OrderItem]


@app.get("/api/health")
def health():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.get("/api/categories")
def categories():
    rows, _ = fetch_all(
        """
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL AND category <> ''
        ORDER BY category
        """
    )
    return [row["category"] for row in rows]


@app.get("/api/products")
def products(
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    query = """
        SELECT
            product_id,
            name,
            category,
            price,
            stock,
            COALESCE(description, '') AS description,
            COALESCE(image_url, '') AS image_url,
            COALESCE(rating, 4.5) AS rating,
            COALESCE(reviews_count, 0) AS reviews_count
        FROM products
        WHERE 1=1
    """
    params = []

    if search.strip():
        query += " AND (name ILIKE %s OR category ILIKE %s)"
        term = f"%{search.strip()}%"
        params.extend([term, term])

    if category.strip():
        query += " AND category = %s"
        params.append(category.strip())

    query += " ORDER BY product_id DESC LIMIT 40"

    rows, _ = fetch_all(
    query,
    params,
    search_term=search.strip() if search.strip() else None
)   
    return rows


@app.get("/api/products/{product_id}")
def product(product_id: int):
    row, _ = fetch_one(
        """
        SELECT
            product_id,
            name,
            category,
            price,
            stock,
            COALESCE(description, '') AS description,
            COALESCE(image_url, '') AS image_url,
            COALESCE(rating, 4.5) AS rating,
            COALESCE(reviews_count, 0) AS reviews_count
        FROM products
        WHERE product_id = %s
        """,
        (product_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


@app.get("/api/customers")
def customers(city: str = Query(default="")):
    if not city.strip():
        rows, _ = fetch_all(
            """
            SELECT user_id, name, email, city, created_at
            FROM users
            ORDER BY user_id DESC
            LIMIT 25
            """
        )
        return rows

    # Intentional workload pattern for the Gen-DBA demo:
    # wrapping the indexed city column in LOWER() creates a realistic
    # optimization opportunity for the advisor.
    query = """
        SELECT user_id, name, email, city, created_at
        FROM users
        WHERE LOWER(city) = LOWER(%s)
        ORDER BY user_id DESC
        LIMIT 25
    """
    rows, _ = fetch_all(query, (city.strip(),))
    return rows


@app.get("/api/orders")
def orders(email: Optional[str] = Query(default=None)):
    query = """
        SELECT
            o.order_id,
            o.order_date,
            o.total_amount,
            u.name,
            u.email,
            u.city,
            p.payment_status,
            p.payment_method
        FROM orders o
        JOIN users u ON u.user_id = o.user_id
        LEFT JOIN payments p ON p.order_id = o.order_id
    """
    params = []

    if email and email.strip():
        query += " WHERE u.email = %s"
        params.append(email.strip())

    query += " ORDER BY o.order_date DESC LIMIT 25"

    rows, _ = fetch_all(query, params)
    return rows


@app.post("/api/orders")
def create_order(payload: OrderCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    started = time.perf_counter()

    try:
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s LIMIT 1",
            (payload.email,),
        )
        user = cursor.fetchone()

        if user:
            user_id = user["user_id"]
        else:
            cursor.execute(
                """
                INSERT INTO users (name, email, city)
                VALUES (%s, %s, %s)
                RETURNING user_id
                """,
                (payload.name, payload.email, payload.city),
            )
            user_id = cursor.fetchone()["user_id"]

        total = 0.0
        prepared = []

        for item in payload.items:
            cursor.execute(
                """
                SELECT product_id, name, price, stock
                FROM products
                WHERE product_id = %s
                FOR UPDATE
                """,
                (item.product_id,),
            )
            product = cursor.fetchone()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found",
                )

            if int(product["stock"] or 0) < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product['name']}",
                )

            line_total = float(product["price"]) * item.quantity
            total += line_total
            prepared.append((item, product, line_total))

        cursor.execute(
            """
            INSERT INTO orders (user_id, total_amount)
            VALUES (%s, %s)
            RETURNING order_id, order_date
            """,
            (user_id, round(total, 2)),
        )
        order = cursor.fetchone()

        for item, product, _ in prepared:
            cursor.execute(
                """
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order["order_id"],
                    product["product_id"],
                    item.quantity,
                    product["price"],
                ),
            )

            cursor.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE product_id = %s
                """,
                (item.quantity, product["product_id"]),
            )

        cursor.execute(
            """
            INSERT INTO payments
            (order_id, payment_method, payment_status)
            VALUES (%s, %s, %s)
            """,
            (order["order_id"], "Card", "Paid"),
        )

        conn.commit()

        return {
            "order_id": order["order_id"],
            "order_date": order["order_date"],
            "total_amount": round(total, 2),
            "status": "Confirmed",
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Order creation failed: {e}")
    finally:
        elapsed = (time.perf_counter() - started) * 1000
        cursor.close()
        conn.close()
        log_query("POST /api/orders - transactional order workflow", elapsed)
