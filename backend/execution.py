import os
import psycopg2

from fastapi import HTTPException
from dotenv import load_dotenv

from backend.query_security import validate_query


load_dotenv("backend/.env")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_execution_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# =========================================================
# EXECUTE APPROVED RECOMMENDATION
# =========================================================

def execute_approved_recommendation(
    recommendation_id,
    performed_by="DBA"
):

    conn = get_execution_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # 1. GET RECOMMENDATION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                recommendation_id,
                log_id,
                comparison_id,
                recommendation_text,
                status
            FROM recommendations
            WHERE recommendation_id = %s
            """,
            (recommendation_id,)
        )

        recommendation = cursor.fetchone()

        if not recommendation:

            raise HTTPException(
                status_code=404,
                detail="Recommendation not found."
            )

        rec_id = recommendation[0]
        comparison_id = recommendation[2]
        status = recommendation[4]

        # -------------------------------------------------
        # 2. APPROVAL CHECK
        # -------------------------------------------------

        if status != "APPROVED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Recommendation must be APPROVED "
                    "before execution."
                )
            )

        # -------------------------------------------------
        # 3. COMPARISON CHECK
        # -------------------------------------------------

        if not comparison_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No performance comparison is linked "
                    "to this recommendation."
                )
            )

        cursor.execute(
            """
            SELECT
                optimized_query,
                original_median_time,
                optimized_median_time,
                improvement_percentage,
                validation_status
            FROM performance_comparisons
            WHERE comparison_id = %s
            """,
            (comparison_id,)
        )

        comparison = cursor.fetchone()

        if not comparison:

            raise HTTPException(
                status_code=404,
                detail="Linked performance comparison not found."
            )

        optimized_query = comparison[0]
        original_median = float(
            comparison[1] or 0
        )
        optimized_median = float(
            comparison[2] or 0
        )
        improvement = float(
            comparison[3] or 0
        )
        validation_status = comparison[4]

        # -------------------------------------------------
        # 4. VALIDATION CHECK
        # -------------------------------------------------

        if validation_status != "PASSED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Performance validation must PASS "
                    "before execution."
                )
            )

        # -------------------------------------------------
        # 5. SECURITY CHECK
        # -------------------------------------------------

        is_safe, security_message = validate_query(
            optimized_query
        )

        if not is_safe:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Optimized query blocked by security "
                    f"validation: {security_message}"
                )
            )

        # -------------------------------------------------
        # 6. EXTRA SELECT-ONLY SAFETY CHECK
        # -------------------------------------------------

        normalized_query = (
            optimized_query
            .strip()
            .lower()
        )

        if not normalized_query.startswith("select"):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Controlled execution currently "
                    "supports SELECT queries only."
                )
            )

        # -------------------------------------------------
        # 7. READ-ONLY EXECUTION
        # -------------------------------------------------

        execution_conn = get_execution_connection()

        execution_cursor = None

        try:

            execution_conn.set_session(
                readonly=True,
                autocommit=False
            )

            execution_cursor = (
                execution_conn.cursor()
            )

            execution_cursor.execute(
                "EXPLAIN (ANALYZE, FORMAT JSON) "
                + optimized_query
            )

            result = execution_cursor.fetchone()

            if not result:

                raise Exception(
                    "Execution returned no result."
                )

            explain_result = result[0][0]

            actual_execution_time = float(
                explain_result.get(
                    "Execution Time",
                    0
                )
            )

            execution_conn.rollback()

        except Exception as e:

            try:
                execution_conn.rollback()
            except Exception:
                pass

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Controlled execution failed: {str(e)}"
                )
            )

        finally:

            if execution_cursor:
                execution_cursor.close()

            execution_conn.close()

        # -------------------------------------------------
        # 8. EXECUTION STATUS
        # -------------------------------------------------

        if (
            optimized_median > 0
            and actual_execution_time
            <= optimized_median * 1.5
        ):

            execution_status = "VERIFIED"

        else:

            execution_status = "REVIEW_REQUIRED"

        # -------------------------------------------------
        # 9. SAVE EXECUTION LOG
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO execution_logs
            (
                recommendation_id,
                comparison_id,
                execution_type,
                status,
                execution_time,
                message,
                performed_by
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING execution_id
            """,
            (
                rec_id,
                comparison_id,
                "READ_ONLY_VALIDATION",
                execution_status,
                actual_execution_time,
                (
                    "Approved optimized query was executed "
                    "in read-only validation mode."
                ),
                performed_by
            )
        )

        execution_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # 10. AUDIT LOG
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO audit_logs
            (
                recommendation_id,
                action,
                performed_by,
                details
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            RETURNING audit_id
            """,
            (
                rec_id,
                "CONTROLLED_EXECUTION",
                performed_by,
                (
                    f"Approved recommendation executed in "
                    f"read-only validation mode. "
                    f"Execution ID: {execution_id}. "
                    f"Observed time: "
                    f"{actual_execution_time:.3f} ms."
                )
            )
        )

        audit_id = cursor.fetchone()[0]

        conn.commit()

        # -------------------------------------------------
        # 11. FINAL RESULT
        # -------------------------------------------------

        return {
            "execution_id": execution_id,
            "recommendation_id": rec_id,
            "comparison_id": comparison_id,
            "execution_status": execution_status,
            "execution_type": "READ_ONLY_VALIDATION",
            "performed_by": performed_by,
            "original_median_time": original_median,
            "optimized_median_time": optimized_median,
            "observed_execution_time": round(
                actual_execution_time,
                3
            ),
            "improvement_percentage": improvement,
            "audit_id": audit_id,
            "message": (
                "Approved optimized query was successfully "
                "validated in read-only mode."
            )
        }

    except HTTPException:

        conn.rollback()

        raise

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Execution operation failed: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()


# =========================================================
# GET EXECUTION HISTORY
# =========================================================

def get_execution_history(limit=20):

    conn = get_execution_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                e.execution_id,
                e.recommendation_id,
                e.comparison_id,
                e.execution_type,
                e.status,
                e.execution_time,
                e.message,
                e.performed_by,
                e.created_at,

                p.original_median_time,
                p.optimized_median_time,
                p.improvement_percentage

            FROM execution_logs e

            LEFT JOIN performance_comparisons p
                ON e.comparison_id = p.comparison_id

            ORDER BY e.execution_id DESC

            LIMIT %s
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        history = []

        for row in rows:

            history.append({
                "execution_id": row[0],
                "recommendation_id": row[1],
                "comparison_id": row[2],
                "execution_type": row[3],
                "status": row[4],
                "execution_time": float(row[5] or 0),
                "message": row[6],
                "performed_by": row[7],
                "created_at": row[8],

                "original_median_time":
                    float(row[9] or 0),

                "optimized_median_time":
                    float(row[10] or 0),

                "improvement_percentage":
                    float(row[11] or 0)
            })

        return {
            "total": len(history),
            "execution_history": history
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch execution history: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()

        