import statistics

from backend.query_security import validate_query


def run_query(conn, query):
    cursor = conn.cursor()

    cursor.execute(
        query
    )

    rows = cursor.fetchall()

    columns = [
        desc[0]
        for desc in cursor.description
    ]

    cursor.close()

    return columns, rows


def normalize_rows(columns, rows):
    normalized = []

    for row in rows:
        item = {}

        for index, column in enumerate(columns):
            item[column] = row[index]

        normalized.append(item)

    return normalized


def validate_results(
    original_columns,
    original_rows,
    optimized_columns,
    optimized_rows
):
    if original_columns != optimized_columns:
        return False

    original_normalized = normalize_rows(
        original_columns,
        original_rows
    )

    optimized_normalized = normalize_rows(
        optimized_columns,
        optimized_rows
    )

    original_normalized.sort(
        key=lambda x: str(x)
    )

    optimized_normalized.sort(
        key=lambda x: str(x)
    )

    return (
        original_normalized
        == optimized_normalized
    )


def benchmark_query(
    get_connection,
    query,
    runs=3
):

    is_safe, message = validate_query(query)

    if not is_safe:
        raise ValueError(message)

    execution_times = []

    for _ in range(runs):

        conn = get_connection()

        try:

            conn.set_session(
                readonly=True,
                autocommit=False
            )

            cursor = conn.cursor()

            cursor.execute(
                "EXPLAIN (ANALYZE, FORMAT JSON) "
                + query
            )

            result = cursor.fetchone()

            if not result:
                raise ValueError(
                    "No execution result returned."
                )

            explain_result = result[0][0]

            execution_time = float(
                explain_result["Execution Time"]
            )

            execution_times.append(
                execution_time
            )

            cursor.close()
            conn.rollback()

        finally:
            conn.close()

    return {
        "runs": runs,
        "execution_times": execution_times,
        "median_time": round(
            statistics.median(
                execution_times
            ),
            3
        )
    }