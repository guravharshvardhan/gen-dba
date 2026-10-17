def get_dashboard_summary(get_connection):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # =================================================
        # 1. TOTAL ANALYZED QUERY EXECUTIONS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM query_logs
            """
        )

        total_queries = cursor.fetchone()[0]

        # =================================================
        # 2. HIGH / CRITICAL RISK
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM query_logs
            WHERE risk_score >= 60
            """
        )

        high_risk_queries = cursor.fetchone()[0]

        # =================================================
        # 3. MEDIUM RISK
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM query_logs
            WHERE risk_score >= 30
              AND risk_score < 60
            """
        )

        medium_risk_queries = cursor.fetchone()[0]

        # =================================================
        # 4. PENDING RECOMMENDATIONS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM recommendations
            WHERE status = 'PENDING'
            """
        )

        pending_recommendations = (
            cursor.fetchone()[0]
        )

        # =================================================
        # 5. APPROVED RECOMMENDATIONS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM recommendations
            WHERE status = 'APPROVED'
            """
        )

        approved_recommendations = (
            cursor.fetchone()[0]
        )

        # =================================================
        # 6. REJECTED RECOMMENDATIONS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM recommendations
            WHERE status = 'REJECTED'
            """
        )

        rejected_recommendations = (
            cursor.fetchone()[0]
        )

        # =================================================
        # 7. AVERAGE EXECUTION TIME
        # =================================================

        cursor.execute(
            """
            SELECT
                COALESCE(
                    ROUND(
                        AVG(execution_time),
                        3
                    ),
                    0
                )
            FROM query_logs
            """
        )

        average_execution_time = float(
            cursor.fetchone()[0]
        )

        # =================================================
        # 8. TOP UNIQUE IMPACTFUL QUERIES
        # =================================================

        cursor.execute(
            """
            SELECT
                query_text,
                COUNT(*) AS frequency,
                AVG(execution_time) AS avg_execution_time,
                SUM(execution_time) AS total_execution_time,
                MAX(risk_score) AS risk_score
            FROM query_logs
            GROUP BY query_text
            ORDER BY total_execution_time DESC
            LIMIT 5
            """
        )

        top_query_rows = cursor.fetchall()

        top_queries = []

        for rank, row in enumerate(
            top_query_rows,
            start=1
        ):

            query_text = row[0]
            frequency = int(row[1])

            avg_execution_time = float(
                row[2]
            )

            total_execution_time = float(
                row[3]
            )

            risk_score = float(
                row[4] or 0
            )

            if risk_score >= 60:
                priority = "Critical"

            elif risk_score >= 30:
                priority = "High"

            else:
                priority = "Low"

            top_queries.append({
                "rank": rank,
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
                "priority":
                    priority
            })

        # =================================================
        # 9. RECENT RECOMMENDATIONS
        # =================================================

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
            LIMIT 5
            """
        )

        recommendation_rows = (
            cursor.fetchall()
        )

        recent_recommendations = []

        for row in recommendation_rows:

            recent_recommendations.append({
                "recommendation_id":
                    row[0],

                "log_id":
                    row[1],

                "comparison_id":
                    row[2],

                "risk_level":
                    row[3],

                "status":
                    row[4],

                "created_at":
                    str(row[5]),

                "reviewed_at":
                    (
                        str(row[6])
                        if row[6]
                        else None
                    ),

                "recommendation_text":
                    row[7]
            })

        # =================================================
        # 10. RECENT AUDIT LOGS
        # =================================================

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
            LIMIT 5
            """
        )

        audit_rows = cursor.fetchall()

        recent_audit_logs = []

        for row in audit_rows:

            recent_audit_logs.append({
                "audit_id":
                    row[0],

                "recommendation_id":
                    row[1],

                "action":
                    row[2],

                "performed_by":
                    row[3],

                "details":
                    row[4],

                "created_at":
                    str(row[5])
            })

        # =================================================
        # 11. FINAL DASHBOARD RESPONSE
        # =================================================

        return {
            "summary": {

                "total_queries":
                    total_queries,

                "high_risk_queries":
                    high_risk_queries,

                "medium_risk_queries":
                    medium_risk_queries,

                "pending_recommendations":
                    pending_recommendations,

                "approved_recommendations":
                    approved_recommendations,

                "rejected_recommendations":
                    rejected_recommendations,

                "average_execution_time":
                    average_execution_time
            },

            "top_queries":
                top_queries,

            "recent_recommendations":
                recent_recommendations,

            "recent_audit_logs":
                recent_audit_logs
        }

    finally:

        cursor.close()
        conn.close()