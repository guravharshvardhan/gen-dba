def validate_query(query):
    query = query.strip().lower()

    if not query.startswith("select"):
        return False, "Only SELECT queries are allowed."

    blocked_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke"
    ]

    for keyword in blocked_keywords:
        if f" {keyword} " in f" {query} ":
            return False, f"Blocked SQL operation: {keyword}"

    return True, "Query is safe."