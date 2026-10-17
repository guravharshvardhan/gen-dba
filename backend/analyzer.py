def analyze_plan(plan):
    issues = []

    def add_issue(
        issue_type,
        severity,
        node_type,
        table,
        explanation,
        suggested_action,
        confidence
    ):
        issues.append({
            "issue_type": issue_type,
            "severity": severity,
            "node_type": node_type,
            "table": table,
            "explanation": explanation,
            "suggested_action": suggested_action,
            "confidence": confidence
        })

    def inspect_node(node, is_root=False):

        node_type = node.get("Node Type", "")
        relation_name = node.get("Relation Name", "N/A")

        total_cost = float(node.get("Total Cost", 0) or 0)
        planned_rows = int(node.get("Plan Rows", 0) or 0)
        actual_rows = int(node.get("Actual Rows", 0) or 0)
        actual_time = float(node.get("Actual Total Time", 0) or 0)

        loops = int(node.get("Actual Loops", 1) or 1)

        rows_removed = int(
            node.get("Rows Removed by Filter", 0) or 0
        )

        shared_read_blocks = int(
            node.get("Shared Read Blocks", 0) or 0
        )

        shared_hit_blocks = int(
            node.get("Shared Hit Blocks", 0) or 0
        )

        sort_space_type = node.get(
            "Sort Space Type", ""
        )

        filter_condition = node.get("Filter")

        total_examined = (
            (actual_rows + rows_removed) * loops
        )

        # --------------------------------------------------
        # 1. Inefficient Sequential Scan
        # --------------------------------------------------

        if node_type == "Seq Scan":

            # No filter means scanning the whole table may be correct.
            if filter_condition and total_examined > 5000:

                filtered_ratio = (
                    rows_removed / total_examined
                    if total_examined > 0
                    else 0
                )

                if filtered_ratio >= 0.50:

                    confidence = min(
                        95,
                        70 + int(filtered_ratio * 25)
                    )

                    add_issue(
                        "Sequential Scan",
                        "Medium",
                        node_type,
                        relation_name,
                        "A large portion of the scanned rows is being filtered out after the table scan.",
                        "Review the filter condition and consider an appropriate index.",
                        confidence
                    )

        # --------------------------------------------------
        # 2. High Query Cost
        # --------------------------------------------------

        if is_root and total_cost > 1000:

            confidence = min(
                98,
                60 + int(min(total_cost / 1000, 3) * 12)
            )

            add_issue(
                "High Query Cost",
                "High",
                node_type,
                relation_name,
                "The estimated execution cost of the query is high.",
                "Review the execution plan and optimize the most expensive operations.",
                confidence
            )

        # --------------------------------------------------
        # 3. Nested Loop Join
        # --------------------------------------------------

        if node_type == "Nested Loop":

            if actual_rows > 5000 or actual_time > 5:

                confidence = min(
                    95,
                    65
                    + (15 if actual_rows > 10000 else 0)
                    + (15 if actual_time > 10 else 0)
                )

                add_issue(
                    "Nested Loop Join",
                    "Medium",
                    node_type,
                    relation_name,
                    "A nested loop join is processing a significant amount of data or taking noticeable execution time.",
                    "Review join conditions, filtering, indexes, and whether another join strategy may be more efficient.",
                    confidence
                )

        # --------------------------------------------------
        # 4. Row Estimate Mismatch
        # --------------------------------------------------

        if planned_rows > 0 and actual_rows > 0:

            ratio = max(
                actual_rows / planned_rows,
                planned_rows / actual_rows
            )

            if ratio >= 5:

                confidence = min(
                    98,
                    65 + int(min(ratio / 5, 6) * 5)
                )

                add_issue(
                    "Row Estimate Mismatch",
                    "High",
                    node_type,
                    relation_name,
                    "The estimated number of rows differs significantly from the actual number of rows.",
                    "Review database statistics and query selectivity.",
                    confidence
                )

        # --------------------------------------------------
        # 5. Expensive Sort
        # --------------------------------------------------

        if node_type == "Sort":

            if actual_rows > 1000 and actual_time > 5:

                confidence = min(
                    95,
                    70
                    + (10 if actual_rows > 10000 else 0)
                    + (10 if actual_time > 20 else 0)
                )

                add_issue(
                    "Expensive Sort",
                    "Medium",
                    node_type,
                    relation_name,
                    "A large number of rows are being sorted and the sort operation takes noticeable execution time.",
                    "Review filtering, ordering requirements, and whether an appropriate index can reduce sorting work.",
                    confidence
                )

        # --------------------------------------------------
        # 6. High Rows Processed
        # --------------------------------------------------

        if actual_rows > 10000:

            if node_type in [
                "Hash Join",
                "Nested Loop",
                "Sort",
                "Seq Scan"
            ]:

                confidence = min(
                    95,
                    70 + min(int(actual_rows / 10000) * 5, 25)
                )

                add_issue(
                    "High Rows Processed",
                    "High",
                    node_type,
                    relation_name,
                    "A large number of rows are being processed by this execution step.",
                    "Reduce unnecessary rows using filtering, better query structure, or appropriate indexing where applicable.",
                    confidence
                )

        # --------------------------------------------------
        # 7. Potential Missing Index
        # --------------------------------------------------

        if node_type == "Seq Scan" and filter_condition:

            if total_examined > 1000:

                filtered_ratio = (
                    rows_removed / total_examined
                    if total_examined > 0
                    else 0
                )

                if filtered_ratio >= 0.50:

                    confidence = min(
                        95,
                        70 + int(filtered_ratio * 20)
                    )

                    add_issue(
                        "Potential Missing Index",
                        "Medium",
                        node_type,
                        relation_name,
                        "A filtered sequential scan is processing many rows that are later discarded, which may indicate that the existing indexing strategy is not effective for this filter.",
                        "Review the filter expression and existing indexes before creating a new index.",
                        confidence
                    )

        # --------------------------------------------------
        # 8. High I/O
        # --------------------------------------------------

        if shared_read_blocks > 5000:

            confidence = min(
                98,
                70 + int(min(shared_read_blocks / 5000, 5) * 5)
            )

            add_issue(
                "High I/O",
                "High",
                node_type,
                relation_name,
                "The execution step is reading a large number of data blocks from disk.",
                "Review indexes, filtering, query structure, and unnecessary data access.",
                confidence
            )

        # --------------------------------------------------
        # 9. Disk Sort Spill
        # --------------------------------------------------

        if (
            node_type == "Sort"
            and sort_space_type == "Disk"
        ):

            add_issue(
                "Disk Sort Spill",
                "High",
                node_type,
                relation_name,
                "The sort operation is using disk space instead of remaining entirely in memory.",
                "Review sort size, work_mem, filtering, and indexing strategy.",
                98
            )

        # --------------------------------------------------
        # 10. High Filtered Rows
        # --------------------------------------------------

        if rows_removed > 10000:

            confidence = min(
                98,
                70 + int(min(rows_removed / 10000, 5) * 5)
            )

            add_issue(
                "High Filtered Rows",
                "Medium",
                node_type,
                relation_name,
                "A large number of rows are being processed and then removed by a filter.",
                "Review filtering conditions and consider an indexing strategy that can reduce unnecessary row scanning.",
                confidence
            )

        # --------------------------------------------------
        # 11. Expensive Hash Join
        # --------------------------------------------------

        if node_type == "Hash Join":

            peak_memory = int(
                node.get("Peak Memory Usage", 0) or 0
            )

            if (
                actual_rows > 10000
                and (
                    actual_time > 5
                    or peak_memory > 50000
                )
            ):

                confidence = min(
                    95,
                    70
                    + (10 if actual_time > 10 else 0)
                    + (10 if peak_memory > 50000 else 0)
                )

                add_issue(
                    "Expensive Hash Join",
                    "Medium",
                    node_type,
                    relation_name,
                    "The hash join is processing a large dataset and may consume significant execution resources.",
                    "Review filtering, join conditions, data volume, and memory usage before changing the join strategy.",
                    confidence
                )

        # --------------------------------------------------
        # Recursively inspect child nodes
        # --------------------------------------------------

        for child in node.get("Plans", []):
            inspect_node(child, False)

    # Start with root node
    inspect_node(plan, True)

    return issues