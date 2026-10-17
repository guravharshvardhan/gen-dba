import os
import re
import psycopg2

from fastapi import HTTPException
from dotenv import load_dotenv


load_dotenv("backend/.env")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_optimization_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# =========================================================
# CREATE OPTIMIZATION ACTION
# =========================================================

def create_optimization_action(
    recommendation_id,
    action_type,
    target_table,
    target_column,
    action_sql,
    rollback_sql
):

    conn = get_optimization_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # CHECK RECOMMENDATION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                recommendation_id,
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

        if recommendation[1] != "APPROVED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Recommendation must be APPROVED "
                    "before creating an optimization action."
                )
            )

        # -------------------------------------------------
        # ALLOWED ACTION TYPE
        # -------------------------------------------------

        if action_type != "CREATE_INDEX":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only CREATE_INDEX actions are "
                    "supported currently."
                )
            )

        # -------------------------------------------------
        # BASIC SQL VALIDATION
        # -------------------------------------------------

        normalized_action = (
            action_sql.strip().rstrip(";").strip()
        )

        normalized_rollback = (
            rollback_sql.strip().rstrip(";").strip()
        )

        create_pattern = re.compile(
            r"^CREATE\s+INDEX\s+[A-Za-z_][A-Za-z0-9_]*\s+"
            r"ON\s+[A-Za-z_][A-Za-z0-9_]*\s*"
            r"\([A-Za-z_][A-Za-z0-9_]*\)$",
            re.IGNORECASE
        )

        drop_pattern = re.compile(
            r"^DROP\s+INDEX(\s+IF\s+EXISTS)?\s+"
            r"[A-Za-z_][A-Za-z0-9_]*$",
            re.IGNORECASE
        )

        if not create_pattern.match(
            normalized_action
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid CREATE INDEX action format."
                )
            )

        if not drop_pattern.match(
            normalized_rollback
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid DROP INDEX rollback format."
                )
            )

        # -------------------------------------------------
        # SAVE ACTION
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO optimization_actions
            (
                recommendation_id,
                action_type,
                target_table,
                target_column,
                action_sql,
                rollback_sql,
                status,
                approved_by
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'PENDING',
                'DBA'
            )
            RETURNING action_id
            """,
            (
                recommendation_id,
                action_type,
                target_table,
                target_column,
                action_sql,
                rollback_sql
            )
        )

        action_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # AUDIT
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
            """,
            (
                recommendation_id,
                "OPTIMIZATION_ACTION_CREATED",
                "DBA",
                (
                    f"Optimization action #{action_id} "
                    f"created for recommendation "
                    f"#{recommendation_id}."
                )
            )
        )

        conn.commit()

        return {
            "action_id": action_id,
            "recommendation_id": recommendation_id,
            "action_type": action_type,
            "target_table": target_table,
            "target_column": target_column,
            "status": "PENDING",
            "message": (
                "Optimization action created successfully."
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
                f"Failed to create optimization action: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()


# =========================================================
# EXECUTE OPTIMIZATION ACTION
# =========================================================

def execute_optimization_action(
    action_id,
    performed_by="DBA"
):

    conn = get_optimization_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # GET ACTION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                action_id,
                recommendation_id,
                action_type,
                target_table,
                target_column,
                action_sql,
                rollback_sql,
                status
            FROM optimization_actions
            WHERE action_id = %s
            """,
            (action_id,)
        )

        action = cursor.fetchone()

        if not action:

            raise HTTPException(
                status_code=404,
                detail="Optimization action not found."
            )

        recommendation_id = action[1]
        action_type = action[2]
        target_table = action[3]
        target_column = action[4]
        action_sql = action[5]
        rollback_sql = action[6]
        status = action[7]

        # -------------------------------------------------
        # STATUS CHECK
        # -------------------------------------------------

        if status != "PENDING":

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Optimization action is already {status}."
                )
            )

        # -------------------------------------------------
        # APPROVAL CHECK
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT status
            FROM recommendations
            WHERE recommendation_id = %s
            """,
            (recommendation_id,)
        )

        recommendation = cursor.fetchone()

        if not recommendation:

            raise HTTPException(
                status_code=404,
                detail="Linked recommendation not found."
            )

        if recommendation[0] != "APPROVED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Linked recommendation is not APPROVED."
                )
            )

        # -------------------------------------------------
        # ACTION TYPE CHECK
        # -------------------------------------------------

        if action_type != "CREATE_INDEX":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only CREATE_INDEX execution is "
                    "supported currently."
                )
            )

        # -------------------------------------------------
        # SQL VALIDATION
        # -------------------------------------------------

        normalized_action = (
            action_sql.strip().rstrip(";").strip()
        )

        create_pattern = re.compile(
            r"^CREATE\s+INDEX\s+[A-Za-z_][A-Za-z0-9_]*\s+"
            r"ON\s+[A-Za-z_][A-Za-z0-9_]*\s*"
            r"\([A-Za-z_][A-Za-z0-9_]*\)$",
            re.IGNORECASE
        )

        if not create_pattern.match(
            normalized_action
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only safe CREATE INDEX statements "
                    "are allowed."
                )
            )

        if not rollback_sql:

            raise HTTPException(
                status_code=400,
                detail="Rollback SQL is missing."
            )

        # -------------------------------------------------
        # EXECUTE
        # -------------------------------------------------

        cursor.execute(action_sql)

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE optimization_actions
            SET
                status = 'EXECUTED',
                approved_by = %s,
                executed_at = CURRENT_TIMESTAMP
            WHERE action_id = %s
            """,
            (
                performed_by,
                action_id
            )
        )

        # -------------------------------------------------
        # EXECUTION LOG
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO execution_logs
            (
                recommendation_id,
                execution_type,
                status,
                message,
                performed_by
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING execution_id
            """,
            (
                recommendation_id,
                "OPTIMIZATION_EXECUTION",
                "EXECUTED",
                (
                    f"Optimization action #{action_id} "
                    f"executed. Type: {action_type}. "
                    f"Target: {target_table}.{target_column}."
                ),
                performed_by
            )
        )

        execution_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # AUDIT
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
            """,
            (
                recommendation_id,
                "OPTIMIZATION_EXECUTED",
                performed_by,
                (
                    f"Optimization action #{action_id} "
                    f"executed successfully. "
                    f"Execution ID: {execution_id}."
                )
            )
        )

        conn.commit()

        return {
            "action_id": action_id,
            "recommendation_id": recommendation_id,
            "action_type": action_type,
            "target_table": target_table,
            "target_column": target_column,
            "status": "EXECUTED",
            "execution_id": execution_id,
            "message": (
                "Optimization action executed successfully."
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
                f"Optimization execution failed: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()


# =========================================================
# ROLLBACK OPTIMIZATION
# =========================================================

def rollback_optimization_action(
    action_id,
    performed_by="DBA"
):

    conn = get_optimization_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # GET ACTION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                action_id,
                recommendation_id,
                action_type,
                rollback_sql,
                status
            FROM optimization_actions
            WHERE action_id = %s
            """,
            (action_id,)
        )

        action = cursor.fetchone()

        if not action:

            raise HTTPException(
                status_code=404,
                detail="Optimization action not found."
            )

        recommendation_id = action[1]
        action_type = action[2]
        rollback_sql = action[3]
        status = action[4]

        if status not in [
            "EXECUTED",
            "DEGRADED"
        ]:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only an executed optimization action "
                    "can be rolled back."
                )
            )

        # -------------------------------------------------
        # ROLLBACK SQL VALIDATION
        # -------------------------------------------------

        normalized_rollback = (
            rollback_sql.strip().rstrip(";").strip()
        )

        drop_pattern = re.compile(
            r"^DROP\s+INDEX(\s+IF\s+EXISTS)?\s+"
            r"[A-Za-z_][A-Za-z0-9_]*$",
            re.IGNORECASE
        )

        if not drop_pattern.match(
            normalized_rollback
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only safe DROP INDEX rollback "
                    "statements are allowed."
                )
            )

        # -------------------------------------------------
        # EXECUTE ROLLBACK
        # -------------------------------------------------

        cursor.execute(rollback_sql)

        # -------------------------------------------------
        # UPDATE ACTION
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE optimization_actions
            SET status = 'ROLLED_BACK'
            WHERE action_id = %s
            """,
            (action_id,)
        )

        # -------------------------------------------------
        # EXECUTION LOG
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO execution_logs
            (
                recommendation_id,
                execution_type,
                status,
                message,
                performed_by
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING execution_id
            """,
            (
                recommendation_id,
                "AUTOMATIC_ROLLBACK",
                "ROLLED_BACK",
                (
                    f"Optimization action #{action_id} "
                    f"was rolled back."
                ),
                performed_by
            )
        )

        execution_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # AUDIT
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
            """,
            (
                recommendation_id,
                "OPTIMIZATION_ROLLBACK",
                performed_by,
                (
                    f"Optimization action #{action_id} "
                    f"was rolled back automatically. "
                    f"Execution ID: {execution_id}."
                )
            )
        )

        conn.commit()

        return {
            "action_id": action_id,
            "recommendation_id": recommendation_id,
            "action_type": action_type,
            "status": "ROLLED_BACK",
            "execution_id": execution_id,
            "message": (
                "Optimization action rolled back successfully."
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
                f"Rollback failed: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()


# =========================================================
# BENCHMARK HELPER
# =========================================================

def benchmark_query(
    query,
    runs=3
):

    conn = get_optimization_connection()

    cursor = None

    try:

        conn.set_session(
            readonly=True,
            autocommit=False
        )

        cursor = conn.cursor()

        times = []

        for _ in range(runs):

            cursor.execute(
                "EXPLAIN (ANALYZE, FORMAT JSON) "
                + query
            )

            result = cursor.fetchone()

            if not result:

                raise Exception(
                    "No benchmark result returned."
                )

            plan_data = result[0][0]

            execution_time = float(
                plan_data.get(
                    "Execution Time",
                    0
                )
            )

            times.append(
                round(
                    execution_time,
                    3
                )
            )

        conn.rollback()

        sorted_times = sorted(times)

        middle = len(sorted_times) // 2

        if len(sorted_times) % 2 == 1:

            median_time = sorted_times[middle]

        else:

            median_time = (
                sorted_times[middle - 1]
                + sorted_times[middle]
            ) / 2

        return (
            times,
            round(
                median_time,
                3
            )
        )

    finally:

        if cursor:
            cursor.close()

        conn.close()


# =========================================================
# FINALIZE OPTIMIZATION
# =========================================================

def finalize_optimization_action(
    action_id,
    performed_by="SYSTEM"
):

    conn = get_optimization_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # 1. GET ACTION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                action_id,
                recommendation_id,
                status
            FROM optimization_actions
            WHERE action_id = %s
            """,
            (action_id,)
        )

        action = cursor.fetchone()

        if not action:

            raise HTTPException(
                status_code=404,
                detail="Optimization action not found."
            )

        recommendation_id = action[1]
        action_status = action[2]

        if action_status != "EXECUTED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only an EXECUTED optimization action "
                    "can be finalized."
                )
            )

        # -------------------------------------------------
        # 2. GET COMPARISON
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                r.comparison_id,
                p.original_query,
                p.optimized_query
            FROM recommendations r
            JOIN performance_comparisons p
                ON r.comparison_id = p.comparison_id
            WHERE r.recommendation_id = %s
            """,
            (recommendation_id,)
        )

        comparison = cursor.fetchone()

        if not comparison:

            raise HTTPException(
                status_code=404,
                detail=(
                    "No performance comparison is linked "
                    "to this recommendation."
                )
            )

        comparison_id = comparison[0]
        original_query = comparison[1]
        optimized_query = comparison[2]

        # -------------------------------------------------
        # 3. BENCHMARK ORIGINAL
        # -------------------------------------------------

        original_times, original_median = (
            benchmark_query(
                original_query,
                runs=3
            )
        )

        # -------------------------------------------------
        # 4. BENCHMARK OPTIMIZED
        # -------------------------------------------------

        optimized_times, optimized_median = (
            benchmark_query(
                optimized_query,
                runs=3
            )
        )

        # -------------------------------------------------
        # 5. IMPROVEMENT
        # -------------------------------------------------

        if original_median > 0:

            improvement = (
                (
                    original_median
                    - optimized_median
                )
                / original_median
            ) * 100

        else:

            improvement = 0

        improvement = round(
            improvement,
            2
        )

        # -------------------------------------------------
        # 6. DECISION
        # -------------------------------------------------

        if optimized_median < original_median:

            verification_status = "IMPROVED"

            action_final_status = "VERIFIED"

            # No rollback

            rollback_result = None

        else:

            verification_status = "DEGRADED"

            action_final_status = "DEGRADED"

            # -------------------------------------------------
            # AUTOMATIC ROLLBACK
            # -------------------------------------------------

            rollback_result = rollback_optimization_action(
                action_id,
                performed_by="SYSTEM"
            )

            action_final_status = "ROLLED_BACK"

        # -------------------------------------------------
        # 7. UPDATE COMPARISON
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE performance_comparisons
            SET
                original_median_time = %s,
                optimized_median_time = %s,
                improvement_percentage = %s,
                validation_status = %s
            WHERE comparison_id = %s
            """,
            (
                original_median,
                optimized_median,
                improvement,
                (
                    "PASSED"
                    if verification_status == "IMPROVED"
                    else "FAILED"
                ),
                comparison_id
            )
        )

        # -------------------------------------------------
        # 8. UPDATE ACTION IF IMPROVED
        # -------------------------------------------------

        if verification_status == "IMPROVED":

            cursor.execute(
                """
                UPDATE optimization_actions
                SET status = 'VERIFIED'
                WHERE action_id = %s
                """,
                (action_id,)
            )

        # -------------------------------------------------
        # 9. FINAL EXECUTION LOG
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
                recommendation_id,
                comparison_id,
                "FINAL_OPTIMIZATION_VERIFICATION",
                action_final_status,
                optimized_median,
                (
                    f"Final benchmark completed. "
                    f"Original median: "
                    f"{original_median:.3f} ms. "
                    f"Optimized median: "
                    f"{optimized_median:.3f} ms. "
                    f"Improvement: "
                    f"{improvement:.2f}%. "
                    f"Decision: "
                    f"{action_final_status}."
                ),
                performed_by
            )
        )

        execution_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # 10. FINAL AUDIT
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
                recommendation_id,
                "OPTIMIZATION_FINALIZED",
                performed_by,
                (
                    f"Optimization finalized. "
                    f"Result: {action_final_status}. "
                    f"Performance improvement: "
                    f"{improvement:.2f}%."
                )
            )
        )

        audit_id = cursor.fetchone()[0]

        conn.commit()

        return {
            "action_id": action_id,
            "recommendation_id": recommendation_id,
            "comparison_id": comparison_id,
            "verification_status": verification_status,
            "final_status": action_final_status,
            "original_times": original_times,
            "optimized_times": optimized_times,
            "original_median": original_median,
            "optimized_median": optimized_median,
            "improvement_percentage": improvement,
            "execution_id": execution_id,
            "audit_id": audit_id,
            "rollback": rollback_result,
            "message": (
                "Optimization finalized successfully."
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
                f"Optimization finalization failed: {str(e)}"
            )
        )

    finally:

        cursor.close()
        conn.close()