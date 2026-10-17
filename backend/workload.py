def calculate_priority(impact_score, max_impact):
    if max_impact <= 0:
        return "Low"

    relative_score = (
        impact_score / max_impact
    ) * 100

    if relative_score >= 80:
        return "Critical"
    elif relative_score >= 50:
        return "High"
    elif relative_score >= 25:
        return "Medium"
    else:
        return "Low"