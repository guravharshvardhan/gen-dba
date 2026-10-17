def calculate_risk(issues):
    severity_weights = {
        "High": 30,
        "Medium": 15,
        "Low": 5
    }

    risk_score = 0

    for issue in issues:

        severity = issue.get("severity", "Low")
        confidence = issue.get("confidence", 50)

        base_score = severity_weights.get(
            severity,
            5
        )

        weighted_score = (
            base_score * confidence / 100
        )

        risk_score += weighted_score

    return round(min(risk_score, 100), 2)


def calculate_impact(execution_time, frequency):
    return round(
        execution_time * frequency,
        3
    )


def calculate_priority(
    impact_score,
    risk_score,
    frequency,
    issue_count
):
    """
    Priority Score combines:
    - workload impact
    - risk
    - frequency
    - number of detected issues
    """

    # Normalize frequency
    frequency_score = min(
        frequency / 100,
        1
    ) * 100

    # Normalize issue count
    issue_score = min(
        issue_count / 10,
        1
    ) * 100

    # Impact is normalized later using max impact
    # Here it is passed as a percentage.
    impact_component = min(
        impact_score,
        100
    )

    priority_score = (
        impact_component * 0.40
        + risk_score * 0.35
        + frequency_score * 0.15
        + issue_score * 0.10
    )

    return round(
        min(priority_score, 100),
        2
    )


def get_priority_level(priority_score):

    if priority_score >= 80:
        return "Critical"

    elif priority_score >= 60:
        return "High"

    elif priority_score >= 30:
        return "Medium"

    else:
        return "Low"