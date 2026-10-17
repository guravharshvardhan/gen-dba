from fastapi import FastAPI, HTTPException, Depends
import psycopg2
from dotenv import load_dotenv
import os

from backend.analyzer import analyze_plan
from backend.scoring import (
    calculate_risk,
    calculate_impact,
    calculate_priority,
    get_priority_level
)
from backend.recommendation import generate_recommendation
from backend.query_security import validate_query
from backend.comparison import (
    validate_results,
    benchmark_query,
    run_query
)
# from backend.approval import update_recommendation_status
from backend.dashboard import get_dashboard_summary
from backend.automation import (
    run_automation,
    get_automation_connection
)
import asyncio
from backend.scheduler import automation_loop
from backend.execution import (
    execute_approved_recommendation,
    get_execution_history
)

from backend.optimization import (
    create_optimization_action,
    execute_optimization_action,
    rollback_optimization_action,
    finalize_optimization_action
)

from backend.auth import (
    ensure_default_users,
    login_user,
    get_current_user,
    require_roles
)

from fastapi import Body

load_dotenv("backend/.env")

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =========================================================
# START AUTOMATION SCHEDULER
# =========================================================

@app.on_event("startup")
async def start_automation_scheduler():

    ensure_default_users()

    asyncio.create_task(
        automation_loop()
    )

# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "message": "Gen-DBA Backend + PostgreSQL Connected"
    }


# =========================================================
# ANALYZE QUERY
# =========================================================

@app.post("/analyze-query")
def analyze_query(query: str):

    # -----------------------------------------------------
    # 1. SECURITY VALIDATION
    # -----------------------------------------------------

    is_safe, security_message = validate_query(query)

    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail=security_message
        )

    # -----------------------------------------------------
    # 2. READ-ONLY QUERY ANALYSIS
    # -----------------------------------------------------

    read_conn = get_connection()

    try:

        read_conn.set_session(
            readonly=True,
            autocommit=False
        )

        read_cursor = read_conn.cursor()

        read_cursor.execute(
            "EXPLAIN (ANALYZE, FORMAT JSON) " + query
        )

        result = read_cursor.fetchone()

        if not result:
            raise Exception(
                "No execution plan returned."
            )

        explain_result = result[0][0]

        plan = explain_result["Plan"]

        execution_time = float(
            explain_result["Execution Time"]
        )

        read_cursor.close()

        read_conn.rollback()

    except Exception as e:

        read_conn.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Query analysis failed: {str(e)}"
        )

    finally:

        read_conn.close()

    # -----------------------------------------------------
    # 3. EXECUTION PLAN ANALYSIS
    # -----------------------------------------------------

    issues = analyze_plan(plan)

    # -----------------------------------------------------
    # 4. RISK SCORE
    # -----------------------------------------------------

    risk_score = calculate_risk(issues)

    # -----------------------------------------------------
    # 5. GET QUERY FREQUENCY
    # -----------------------------------------------------

    frequency_conn = get_connection()

    try:

        frequency_cursor = frequency_conn.cursor()

        frequency_cursor.execute(
            """
            SELECT COUNT(*)
            FROM query_logs
            WHERE query_text = %s
            """,
            (query,)
        )

        previous_count = (
            frequency_cursor.fetchone()[0]
        )

        frequency_cursor.close()

    finally:

        frequency_conn.close()

    frequency = previous_count + 1

    # -----------------------------------------------------
    # 6. IMPACT SCORE
    # -----------------------------------------------------

    impact_score = calculate_impact(
        execution_time,
        frequency
    )

    # -----------------------------------------------------
    # 7. SAVE QUERY + ISSUES
    # -----------------------------------------------------

    write_conn = get_connection()

    try:

        write_cursor = write_conn.cursor()

        write_cursor.execute(
            """
            INSERT INTO query_logs
            (
                query_text,
                execution_time,
                risk_score,
                impact_score
            )
            VALUES
            (%s, %s, %s, %s)
            RETURNING log_id
            """,
            (
                query,
                execution_time,
                risk_score,
                impact_score
            )
        )

        log_id = write_cursor.fetchone()[0]

        # Save issues
        for issue in issues:

            write_cursor.execute(
                """
                INSERT INTO detected_issues
                (
                    log_id,
                    issue_type,
                    severity,
                    node_type,
                    table_name,
                    explanation,
                    suggested_action
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    log_id,
                    issue["issue_type"],
                    issue["severity"],
                    issue.get("node_type"),
                    issue.get("table"),
                    issue["explanation"],
                    issue["suggested_action"]
                )
            )

        write_conn.commit()

    except Exception as e:

        write_conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Database logging failed: {str(e)}"
        )

    finally:

        write_cursor.close()
        write_conn.close()


    # -----------------------------------------------------
    # 8. GEMINI RECOMMENDATION
    # -----------------------------------------------------

    recommendation = None
    ai_recommendation_error = None

    try:
        recommendation = generate_recommendation(
            query,
            plan,
            issues,
            risk_score
        )

        if not recommendation or not recommendation.strip():
            ai_recommendation_error = (
                "Gemini returned an empty recommendation."
            )
            recommendation = None

    except Exception as e:
        ai_recommendation_error = str(e)
        recommendation = None

    # -----------------------------------------------------
    # 9. SAVE RECOMMENDATION ONLY IF AI SUCCEEDS
    # -----------------------------------------------------

    recommendation_id = None
    recommendation_status = "AI_UNAVAILABLE"

    if recommendation is not None:

        recommendation_conn = get_connection()
        recommendation_cursor = None

        try:
            recommendation_cursor = recommendation_conn.cursor()

            if risk_score >= 60:
                risk_level = "High"
            elif risk_score >= 30:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            recommendation_cursor.execute(
                """
                INSERT INTO recommendations
                (
                    log_id,
                    recommendation_text,
                    risk_level,
                    status
                )
                VALUES (%s, %s, %s, %s)
                RETURNING recommendation_id
                """,
                (
                    log_id,
                    recommendation,
                    risk_level,
                    "PENDING"
                )
            )

            recommendation_id = recommendation_cursor.fetchone()[0]
            recommendation_conn.commit()
            recommendation_status = "PENDING"

        except Exception as e:
            recommendation_conn.rollback()

            raise HTTPException(
                status_code=500,
                detail=f"Recommendation save failed: {str(e)}"
            )

        finally:
            if recommendation_cursor is not None:
                recommendation_cursor.close()
            recommendation_conn.close()

    # -----------------------------------------------------
    # 10. FINAL RESPONSE
    # -----------------------------------------------------

    return {
        "query": query,
        "security_status": security_message,
        "execution_plan": plan,
        "issues": issues,
        "risk_score": risk_score,
        "execution_time": execution_time,
        "frequency": frequency,
        "impact_score": impact_score,
        "log_id": log_id,
        "recommendation_id": recommendation_id,
        "recommendation_status": recommendation_status,
        "ai_recommendation": recommendation,
        "ai_recommendation_error": ai_recommendation_error
    }


# =========================================================
# PERFORMANCE TEST HELPER
# =========================================================

def run_performance_test(query):

    is_safe, security_message = validate_query(query)

    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail=security_message
        )

    conn = get_connection()

    try:

        conn.set_session(
            readonly=True,
            autocommit=False
        )

        cursor = conn.cursor()

        cursor.execute(
            "EXPLAIN (ANALYZE, FORMAT JSON) " + query
        )

        result = cursor.fetchone()

        if not result:
            raise Exception(
                "No execution plan returned."
            )

        explain_result = result[0][0]

        plan = explain_result["Plan"]

        execution_time = float(
            explain_result["Execution Time"]
        )

        total_cost = float(
            plan.get("Total Cost", 0)
        )

        cursor.close()

        conn.rollback()

        return {
            "execution_time": execution_time,
            "total_cost": total_cost,
            "plan": plan
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Performance test failed: {str(e)}"
        )

    finally:

        conn.close()


# =========================================================
# COMPARE QUERIES
# =========================================================

@app.post("/compare-queries")
def compare_queries(
    original_query: str,
    optimized_query: str
):

    # -----------------------------------------------------
    # 1. SECURITY VALIDATION
    # -----------------------------------------------------

    original_safe, original_message = (
        validate_query(original_query)
    )

    if not original_safe:
        raise HTTPException(
            status_code=400,
            detail=original_message
        )

    optimized_safe, optimized_message = (
        validate_query(optimized_query)
    )

    if not optimized_safe:
        raise HTTPException(
            status_code=400,
            detail=optimized_message
        )

    # -----------------------------------------------------
    # 2. RESULT VALIDATION
    # -----------------------------------------------------

    validation_conn = get_connection()

    try:

        validation_conn.set_session(
            readonly=True,
            autocommit=False
        )

        original_columns, original_rows = run_query(
            validation_conn,
            original_query
        )

        validation_conn.rollback()

    except Exception as e:

        validation_conn.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Original query validation failed: {str(e)}"
        )

    finally:

        validation_conn.close()

    validation_conn = get_connection()

    try:

        validation_conn.set_session(
            readonly=True,
            autocommit=False
        )

        optimized_columns, optimized_rows = run_query(
            validation_conn,
            optimized_query
        )

        validation_conn.rollback()

    except Exception as e:

        validation_conn.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Optimized query validation failed: {str(e)}"
        )

    finally:

        validation_conn.close()

    validation_status = (
        "PASSED"
        if validate_results(
            original_columns,
            original_rows,
            optimized_columns,
            optimized_rows
        )
        else "FAILED"
    )

    # -----------------------------------------------------
    # 3. BENCHMARK ORIGINAL
    # -----------------------------------------------------

    try:

        original_benchmark = benchmark_query(
            get_connection,
            original_query,
            runs=3
        )

        optimized_benchmark = benchmark_query(
            get_connection,
            optimized_query,
            runs=3
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Benchmark failed: {str(e)}"
        )

    original_median = (
        original_benchmark["median_time"]
    )

    optimized_median = (
        optimized_benchmark["median_time"]
    )

    # -----------------------------------------------------
    # 4. GET COSTS + PLANS
    # -----------------------------------------------------

    original_test = run_performance_test(
        original_query
    )

    optimized_test = run_performance_test(
        optimized_query
    )

    original_cost = (
        original_test["total_cost"]
    )

    optimized_cost = (
        optimized_test["total_cost"]
    )

    # -----------------------------------------------------
    # 5. IMPROVEMENT %
    # -----------------------------------------------------

    if original_median > 0:

        improvement_percentage = (
            (
                original_median
                - optimized_median
            )
            / original_median
        ) * 100

    else:

        improvement_percentage = 0

    improvement_percentage = round(
        improvement_percentage,
        2
    )

    # -----------------------------------------------------
    # 6. PERFORMANCE STATUS
    # -----------------------------------------------------

    if validation_status != "PASSED":

        performance_status = "Validation Failed"

    elif improvement_percentage > 0:

        performance_status = "Improved"

    elif improvement_percentage < 0:

        performance_status = "Regressed"

    else:

        performance_status = "No Improvement"

    # -----------------------------------------------------
    # 7. FIND ORIGINAL LOG
    # -----------------------------------------------------

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT log_id
            FROM query_logs
            WHERE query_text = %s
            ORDER BY log_id DESC
            LIMIT 1
            """,
            (original_query,)
        )

        row = cursor.fetchone()

        log_id = (
            row[0]
            if row
            else None
        )

        # -------------------------------------------------
        # 8. SAVE COMPARISON
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO performance_comparisons
            (
                log_id,
                original_query,
                optimized_query,
                original_execution_time,
                optimized_execution_time,
                original_cost,
                optimized_cost,
                improvement_percentage,
                validation_status,
                benchmark_runs,
                original_median_time,
                optimized_median_time
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
            RETURNING comparison_id
            """,
            (
                log_id,
                original_query,
                optimized_query,
                original_median,
                optimized_median,
                original_cost,
                optimized_cost,
                improvement_percentage,
                validation_status,
                3,
                original_median,
                optimized_median
            )
        )

        comparison_id = cursor.fetchone()[0]

        conn.commit()

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Comparison save failed: {str(e)}"
        )

    finally:

        cursor.close()
        conn.close()

    # -----------------------------------------------------
    # 9. FINAL RESPONSE
    # -----------------------------------------------------

    return {
        "comparison_id": comparison_id,
        "original_query": original_query,
        "optimized_query": optimized_query,
        "validation_status": validation_status,
        "benchmark_runs": 3,
        "original_execution_times":
            original_benchmark["execution_times"],
        "optimized_execution_times":
            optimized_benchmark["execution_times"],
        "original_median_time":
            original_median,
        "optimized_median_time":
            optimized_median,
        "original_cost":
            original_cost,
        "optimized_cost":
            optimized_cost,
        "improvement_percentage":
            improvement_percentage,
        "performance_status":
            performance_status,
        "original_plan":
            original_test["plan"],
        "optimized_plan":
            optimized_test["plan"]
    }


# =========================================================
# WORKLOAD SUMMARY
# =========================================================

@app.get("/workload-summary")
def workload_summary():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                q.query_text,
                COUNT(*) AS frequency,
                AVG(q.execution_time) AS avg_execution_time,
                SUM(q.execution_time) AS total_execution_time,
                MAX(q.risk_score) AS max_risk_score,

                COUNT(
                    DISTINCT d.issue_id
                ) AS issue_count

            FROM query_logs q

            LEFT JOIN detected_issues d
                ON q.log_id = d.log_id

            GROUP BY q.query_text

            ORDER BY total_execution_time DESC

            LIMIT 20
            """
        )

        rows = cursor.fetchall()

        if not rows:

            return {
                "total_queries": 0,
                "workload": []
            }

        # -------------------------------------------------
        # BUILD RAW DATA
        # -------------------------------------------------

        workload_data = []

        for row in rows:

            query_text = row[0]

            frequency = int(row[1])

            avg_execution_time = float(
                row[2] or 0
            )

            total_execution_time = float(
                row[3] or 0
            )

            risk_score = float(
                row[4] or 0
            )

            issue_count = int(
                row[5] or 0
            )

            workload_data.append({
                "query": query_text,
                "frequency": frequency,
                "average_execution_time":
                    round(
                        avg_execution_time,
                        3
                    ),
                "total_execution_time":
                    round(
                        total_execution_time,
                        3
                    ),
                "impact_score":
                    round(
                        total_execution_time,
                        3
                    ),
                "risk_score":
                    round(
                        risk_score,
                        2
                    ),
                "issue_count":
                    issue_count
            })

        # -------------------------------------------------
        # MAX IMPACT
        # -------------------------------------------------

        max_impact = max(
            item["impact_score"]
            for item in workload_data
        )

        workload = []

        # -------------------------------------------------
        # CALCULATE PRIORITY
        # -------------------------------------------------

        for rank, item in enumerate(
            workload_data,
            start=1
        ):

            # Convert impact into relative percentage
            if max_impact > 0:

                impact_percentage = (
                    item["impact_score"]
                    / max_impact
                ) * 100

            else:

                impact_percentage = 0

            priority_score = calculate_priority(
                impact_percentage,
                item["risk_score"],
                item["frequency"],
                item["issue_count"]
            )

            priority = get_priority_level(
                priority_score
            )

            workload.append({
                "rank": rank,

                "query":
                    item["query"],

                "frequency":
                    item["frequency"],

                "average_execution_time":
                    item[
                        "average_execution_time"
                    ],

                "total_execution_time":
                    item[
                        "total_execution_time"
                    ],

                "impact_score":
                    item["impact_score"],

                "impact_percentage":
                    round(
                        impact_percentage,
                        2
                    ),

                "risk_score":
                    item["risk_score"],

                "issue_count":
                    item["issue_count"],

                "priority_score":
                    priority_score,

                "priority":
                    priority
            })

        # Re-sort by priority score
        workload.sort(
            key=lambda x:
                x["priority_score"],
            reverse=True
        )

        # Reassign final ranks
        for index, item in enumerate(
            workload,
            start=1
        ):
            item["rank"] = index

        return {
            "total_queries":
                len(workload),

            "max_impact_score":
                round(
                    max_impact,
                    3
                ),

            "workload":
                workload
        }

    finally:

        cursor.close()
        conn.close()

# =========================================================
# RECOMMENDATION MANAGEMENT
# =========================================================

@app.get("/recommendations")
def get_recommendations():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                recommendation_id,
                log_id,
                comparison_id,
                risk_level,
                status,
                created_at,
                reviewed_at,
                recommendation_text
            FROM recommendations
            ORDER BY recommendation_id DESC
            """
        )

        rows = cursor.fetchall()

        recommendations = []

        for row in rows:

            recommendations.append({
                "recommendation_id": row[0],
                "log_id": row[1],
                "comparison_id": row[2],
                "risk_level": row[3],
                "status": row[4],
                "created_at": row[5],
                "reviewed_at": row[6],
                "recommendation_text": row[7]
            })

        return {
            "total_recommendations":
                len(recommendations),
            "recommendations":
                recommendations
        }

    finally:

        cursor.close()
        conn.close()


# @app.post("/recommendations/{recommendation_id}/approve")
# def approve_recommendation(
#     recommendation_id: int,
#     current_user=Depends(
#         require_roles("ADMIN", "DBA")
#     )
# ):

#     return update_recommendation_status(
#         get_connection,
#         recommendation_id,
#         "APPROVED",
#         performed_by=current_user["username"]
#     )


# @app.post("/recommendations/{recommendation_id}/reject")
# def reject_recommendation(
#     recommendation_id: int,
#     current_user=Depends(
#         require_roles("ADMIN", "DBA")
#     )
# ):

#     return update_recommendation_status(
#         get_connection,
#         recommendation_id,
#         "REJECTED",
#         performed_by=current_user["username"]
#     )



# =========================================================
# APPROVE / REJECT DISABLED FOR SAFETY
# =========================================================

@app.post("/recommendations/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: int):
    raise HTTPException(
        status_code=403,
        detail="Approval is disabled for safety. Recommendations are advisory only."
    )


@app.post("/recommendations/{recommendation_id}/reject")
def reject_recommendation(recommendation_id: int):
    raise HTTPException(
        status_code=403,
        detail="Rejection is disabled for safety. Recommendations are advisory only."
    )

# =========================================================
# AUDIT LOG
# =========================================================

@app.get("/audit-logs")
def get_audit_logs():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                audit_id,
                recommendation_id,
                action,
                performed_by,
                details,
                created_at
            FROM audit_logs
            ORDER BY audit_id DESC
            LIMIT 50
            """
        )

        rows = cursor.fetchall()

        logs = []

        for row in rows:

            logs.append({
                "audit_id": row[0],
                "recommendation_id": row[1],
                "action": row[2],
                "performed_by": row[3],
                "details": row[4],
                "created_at": row[5]
            })

        return {
            "total_logs": len(logs),
            "audit_logs": logs
        }

    finally:

        cursor.close()
        conn.close()

    # =========================================================
# DASHBOARD SUMMARY
# =========================================================

@app.get("/dashboard-summary")
def dashboard_summary():

    return get_dashboard_summary(
        get_connection
    )

# =========================================================
# LINK RECOMMENDATION TO COMPARISON
# =========================================================

@app.post(
    "/recommendations/{recommendation_id}/link-comparison/{comparison_id}"
)
def link_comparison(
    recommendation_id: int,
    comparison_id: int
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # Check recommendation
        cursor.execute(
            """
            SELECT recommendation_id
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

        # Check comparison
        cursor.execute(
            """
            SELECT comparison_id
            FROM performance_comparisons
            WHERE comparison_id = %s
            """,
            (comparison_id,)
        )

        comparison = cursor.fetchone()

        if not comparison:

            raise HTTPException(
                status_code=404,
                detail="Comparison not found."
            )

        # Link
        cursor.execute(
            """
            UPDATE recommendations
            SET comparison_id = %s
            WHERE recommendation_id = %s
            """,
            (
                comparison_id,
                recommendation_id
            )
        )

        conn.commit()

        return {
            "recommendation_id":
                recommendation_id,

            "comparison_id":
                comparison_id,

            "status":
                "Comparison linked successfully."
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Linking failed: {str(e)}"
        )

    finally:

        cursor.close()
        conn.close()

@app.post("/automation/run")
def automation_run(
    limit: int = 5,
    current_user=Depends(
        require_roles("ADMIN", "DBA")
    )
):

    if limit < 1 or limit > 50:

        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 50."
        )

    return run_automation(limit)

# =========================================================
# AUTOMATION HISTORY
# =========================================================

@app.get("/automation/history")
def automation_history(limit: int = 10):

    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 50."
        )

    conn = get_automation_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                run_id,
                started_at,
                completed_at,
                status,
                queries_checked,
                unique_queries_detected,
                recommendations_created,
                already_pending,
                blocked_queries,
                failed_queries
            FROM automation_runs
            ORDER BY run_id DESC
            LIMIT %s
            """,
            (limit,)
        )

        rows = cursor.fetchall()

        history = []

        for row in rows:

            history.append({
                "run_id": row[0],
                "started_at": row[1],
                "completed_at": row[2],
                "status": row[3],
                "queries_checked": row[4],
                "unique_queries_detected": row[5],
                "recommendations_created": row[6],
                "already_pending": row[7],
                "blocked_queries": row[8],
                "failed_queries": row[9]
            })

        return {
            "total_runs": len(history),
            "history": history
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch automation history: {str(e)}"
        )

    finally:

        cursor.close()
        conn.close()


    # =========================================================
# CONTROLLED EXECUTION
# =========================================================

@app.post(
    "/recommendations/{recommendation_id}/execute"
)
def execute_recommendation(
    recommendation_id: int
):

    return execute_approved_recommendation(
        recommendation_id,
        performed_by="DBA"
    )

# =========================================================
# OPTIMIZATION ACTIONS
# =========================================================

@app.post("/optimization-actions")
def create_optimization(
    recommendation_id: int,
    action_type: str,
    target_table: str,
    target_column: str,
    action_sql: str,
    rollback_sql: str,
    current_user=Depends(
        require_roles("ADMIN", "DBA")
    )
):

    return create_optimization_action(
        recommendation_id,
        action_type,
        target_table,
        target_column,
        action_sql,
        rollback_sql
    )


@app.post(
    "/optimization-actions/{action_id}/execute"
)
def execute_optimization(
    action_id: int,
    current_user=Depends(
        require_roles("ADMIN", "DBA")
    )
):

    return execute_optimization_action(
        action_id,
        performed_by=current_user["username"]
    )


@app.post(
    "/optimization-actions/{action_id}/rollback"
)
def rollback_optimization(
    action_id: int,
    current_user=Depends(
        require_roles("ADMIN", "DBA")
    )
):

    return rollback_optimization_action(
        action_id,
        performed_by=current_user["username"]
    )

# =========================================================
# FINALIZE OPTIMIZATION
# =========================================================

@app.post(
    "/optimization-actions/{action_id}/finalize"
)
def finalize_optimization(
    action_id: int,
    current_user=Depends(
        require_roles("ADMIN", "DBA")
    )
):

    return finalize_optimization_action(
        action_id,
        performed_by=current_user["username"]
    )

# =========================================================
# EXECUTION HISTORY
# =========================================================

@app.get("/execution-history")
def execution_history(limit: int = 20):

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100."
        )

    return get_execution_history(limit)

# =========================================================
# AUTHENTICATION
# =========================================================

@app.post("/auth/login")
def auth_login(
    username: str,
    password: str
):

    return login_user(
        username,
        password
    )


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/auth/me")
def auth_me(
    current_user=Depends(
        get_current_user
    )
):

    return current_user

