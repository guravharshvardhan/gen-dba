from fastapi import HTTPException


def update_recommendation_status(
    get_connection,
    recommendation_id,
    new_status,
    performed_by="DBA"
):
    if new_status not in ["APPROVED", "REJECTED"]:
        raise ValueError("Invalid recommendation status.")

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # Check recommendation
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

        current_status = recommendation[1]

        # Prevent changing an already reviewed recommendation
        if current_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Recommendation is already "
                    f"{current_status}."
                )
            )

        # Update recommendation
        cursor.execute(
            """
            UPDATE recommendations
            SET
                status = %s,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE recommendation_id = %s
            """,
            (
                new_status,
                recommendation_id
            )
        )

        # Save audit log
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
            (%s, %s, %s, %s)
            RETURNING audit_id
            """,
            (
                recommendation_id,
                new_status,
                performed_by,
                (
                    f"Recommendation {new_status.lower()} "
                    f"by {performed_by}."
                )
            )
        )

        audit_id = cursor.fetchone()[0]

        conn.commit()

        return {
            "recommendation_id":
                recommendation_id,
            "status":
                new_status,
            "performed_by":
                performed_by,
            "audit_id":
                audit_id
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Approval operation failed: {str(e)}"
        )

    finally:
        cursor.close()
        conn.close()