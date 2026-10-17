import asyncio

from backend.automation import run_automation


# =========================================================
# AUTOMATION SCHEDULER
# =========================================================

async def automation_loop():

    while True:

        try:

            print(
                "\n[AUTOMATION] Running scheduled workload scan..."
            )

            result = run_automation(limit=5)

            print(
                "[AUTOMATION] Scan completed:",
                result.get("queries_checked", 0),
                "queries checked."
            )

        except Exception as e:

            print(
                "[AUTOMATION] Scheduled scan failed:",
                str(e)
            )

        # Wait 5 minutes
        await asyncio.sleep(300)