import json
from backend.gemini_service import ask_gemini


def generate_recommendation(query, plan, issues, risk_score):

    prompt = f"""
You are an expert Database Performance Advisor.

Analyze the following SQL performance information.

SQL Query:
{query}

Detected Issues:
{json.dumps(issues, indent=2)}

Risk Score:
{risk_score}

Execution Plan:
{json.dumps(plan, indent=2)}

Provide a practical optimization recommendation.

Your response must contain:

1. Problem
2. Why it happens
3. Recommended optimization
4. Expected performance benefit
5. Risk of applying the recommendation
6. Security impact

Important rules:
- Do NOT execute SQL.
- Do NOT modify the database.
- Do NOT assume direct database access.
- Only provide advice based on the supplied information.
- Use simple language suitable for a DBA.
"""

    return ask_gemini(prompt)