import os
import psycopg2

from dotenv import load_dotenv

from backend.scoring import calculate_impact
from backend.analyzer import analyze_plan
from backend.query_security import validate_query
from backend.recommendation import generate_recommendation


load_dotenv("backend/.env")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_automation_connection():

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# =========================================================
# SAVE AUTOMATION RUN
# =========================================================

def save_automation_run(
    status,
    queries_checked,
    unique_queries_detected,
    recommendations_created,
    already_pending,
    blocked_queries,
    failed_queries
):

    conn = get_automation_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO automation_runs
            (
                status,
                queries_checked,
                unique_queries_detected,
                recommendations_created,
                already_pending,
                blocked_queries,
                failed_queries,
                completed_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP
            )
            RETURNING run_id
            """,
            (
                status,
                queries_checked,
                unique_queries_detected,
                recommendations_created,
                already_pending,
                blocked_queries,
                failed_queries
            )
        )

        run_id = cursor.fetchone()[0]

        conn.commit()

        return run_id

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()
        conn.close()


# =========================================================
# AUTOMATION ENGINE
# =========================================================

def run_automation(limit=5):

    conn = get_automation_connection()
    cursor = conn.cursor()

    recommendations_created = 0
    already_pending = 0
    blocked_queries = 0
    failed_queries = 0

    try:

        # -------------------------------------------------
        # 1. MERGE SAME QUERIES
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                query_text,
                COUNT(*) AS frequency,
                AVG(execution_time) AS avg_execution_time,
                SUM(execution_time) AS total_execution_time,
                MAX(risk_score) AS risk_score,
                SUM(COALESCE(impact_score, 0)) AS stored_impact
            FROM query_logs
            WHERE query_text IS NOT NULL
            GROUP BY query_text
            ORDER BY
                SUM(COALESCE(impact_score, 0)) DESC,
                MAX(risk_score) DESC
            LIMIT %s
            """,
            (limit,)
        )

        workload_rows = cursor.fetchall()

        candidates = []

        # -------------------------------------------------
        # 2. PROCESS UNIQUE QUERIES
        # -------------------------------------------------

        for row in workload_rows:

            query_text = row[0]

            frequency = int(row[1] or 1)

            average_execution_time = float(
                row[2] or 0
            )

            total_execution_time = float(
                row[3] or 0
            )

            risk_score = float(
                row[4] or 0
            )

            stored_impact = float(
                row[5] or 0
            )

            # -------------------------------------------------
            # IMPACT SCORE
            # -------------------------------------------------

            if stored_impact > 0:

                impact_score = stored_impact

            else:

                impact_score = calculate_impact(
                    average_execution_time,
                    frequency
                )

            # -------------------------------------------------
            # PRIORITY
            # -------------------------------------------------

            if risk_score >= 60 or impact_score >= 50:

                priority = "Critical"

            elif risk_score >= 30 or impact_score >= 25:

                priority = "High"

            elif risk_score >= 10 or impact_score >= 10:

                priority = "Medium"

            else:

                priority = "Low"

            # -------------------------------------------------
            # SECURITY VALIDATION
            # -------------------------------------------------

            is_safe, security_message = validate_query(
                query_text
            )

            candidate = {
                "query": query_text,
                "frequency": frequency,
                "average_execution_time":
                    round(
                        average_execution_time,
                        3
                    ),
                "total_execution_time":
                    round(
                        total_execution_time,
                        3
                    ),
                "impact_score":
                    round(
                        impact_score,
                        3
                    ),
                "risk_score":
                    round(
                        risk_score,
                        2
                    ),
                "priority":
                    priority,
                "security_status":
                    security_message
            }

            # -------------------------------------------------
            # BLOCK UNSAFE QUERY
            # -------------------------------------------------

            if not is_safe:

                candidate["status"] = "BLOCKED"

                blocked_queries += 1

                candidates.append(candidate)

                continue

            # -------------------------------------------------
            # EXECUTION PLAN
            # -------------------------------------------------

            plan_conn = get_automation_connection()

            plan_cursor = None

            try:

                plan_conn.set_session(
                    readonly=True,
                    autocommit=False
                )

                plan_cursor = plan_conn.cursor()

                plan_cursor.execute(
                    "EXPLAIN (ANALYZE, FORMAT JSON) "
                    + query_text
                )

                result = plan_cursor.fetchone()

                if not result:

                    raise Exception(
                        "No execution plan returned."
                    )

                explain_result = result[0][0]

                plan = explain_result["Plan"]

                plan_conn.rollback()

            except Exception as e:

                try:
                    plan_conn.rollback()
                except Exception:
                    pass

                candidate["status"] = "PLAN_FAILED"

                candidate["error"] = str(e)

                failed_queries += 1

                candidates.append(candidate)

                continue

            finally:

                if plan_cursor:
                    plan_cursor.close()

                plan_conn.close()

            # -------------------------------------------------
            # RULE BASED ANALYSIS
            # -------------------------------------------------

            issues = analyze_plan(plan)

            candidate["issue_count"] = len(
                issues
            )

            candidate["issues"] = issues

            # -------------------------------------------------
            # DECIDE WHETHER AI IS REQUIRED
            # -------------------------------------------------

            needs_recommendation = (
                risk_score >= 30
                or impact_score >= 25
                or len(issues) > 0
            )

            if not needs_recommendation:

                candidate["status"] = "MONITORED"

                candidates.append(candidate)

                continue

            # -------------------------------------------------
            # CHECK EXISTING PENDING RECOMMENDATION
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    r.recommendation_id,
                    r.status
                FROM recommendations r
                JOIN query_logs q
                    ON r.log_id = q.log_id
                WHERE
                    q.query_text = %s
                    AND r.status = 'PENDING'
                ORDER BY r.recommendation_id DESC
                LIMIT 1
                """,
                (query_text,)
            )

            existing = cursor.fetchone()

            if existing:

                candidate["status"] = "ALREADY_PENDING"

                candidate["recommendation_id"] = (
                    existing[0]
                )

                already_pending += 1

                candidates.append(candidate)

                continue

            # -------------------------------------------------
            # GEMINI RECOMMENDATION
            # -------------------------------------------------

            try:

                recommendation = generate_recommendation(
                    query_text,
                    plan,
                    issues,
                    risk_score
                )

            except Exception as e:

                candidate["status"] = "AI_FAILED"

                candidate["error"] = str(e)

                failed_queries += 1

                candidates.append(candidate)

                continue

            # -------------------------------------------------
            # GET LATEST LOG
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT log_id
                FROM query_logs
                WHERE query_text = %s
                ORDER BY log_id DESC
                LIMIT 1
                """,
                (query_text,)
            )

            latest_log = cursor.fetchone()

            if not latest_log:

                candidate["status"] = "NO_LOG"

                failed_queries += 1

                candidates.append(candidate)

                continue

            log_id = latest_log[0]

            # -------------------------------------------------
            # RISK LEVEL
            # -------------------------------------------------

            if risk_score >= 60:

                risk_level = "High"

            elif risk_score >= 30:

                risk_level = "Medium"

            else:

                risk_level = "Low"

            # -------------------------------------------------
            # SAVE RECOMMENDATION
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO recommendations
                (
                    log_id,
                    recommendation_text,
                    risk_level,
                    status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'PENDING'
                )
                RETURNING recommendation_id
                """,
                (
                    log_id,
                    recommendation,
                    risk_level
                )
            )

            recommendation_id = cursor.fetchone()[0]

            recommendations_created += 1

            # -------------------------------------------------
            # AUDIT LOG
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
                    "AUTOMATION_RECOMMENDATION_CREATED",
                    "SYSTEM",
                    "Recommendation automatically generated by Gen-DBA automation engine."
                )
            )

            # -------------------------------------------------
            # FINAL CANDIDATE
            # -------------------------------------------------

            candidate["recommendation_id"] = (
                recommendation_id
            )

            candidate["status"] = (
                "RECOMMENDATION_CREATED"
            )

            candidate["recommendation_status"] = (
                "PENDING"
            )

            candidate["ai_recommendation"] = (
                recommendation
            )

            candidates.append(candidate)

        # -------------------------------------------------
        # SAVE TRANSACTION
        # -------------------------------------------------

        conn.commit()

        # -------------------------------------------------
        # SAVE AUTOMATION HISTORY
        # -------------------------------------------------

        run_id = save_automation_run(
            status="COMPLETED",
            queries_checked=len(workload_rows),
            unique_queries_detected=len(workload_rows),
            recommendations_created=recommendations_created,
            already_pending=already_pending,
            blocked_queries=blocked_queries,
            failed_queries=failed_queries
        )

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {
            "automation_status": "COMPLETED",
            "run_id": run_id,
            "queries_checked": len(workload_rows),
            "unique_queries_detected":
                len(workload_rows),
            "recommendations_created":
                recommendations_created,
            "already_pending":
                already_pending,
            "blocked_queries":
                blocked_queries,
            "failed_queries":
                failed_queries,
            "candidates": candidates
        }

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()
        conn.close()