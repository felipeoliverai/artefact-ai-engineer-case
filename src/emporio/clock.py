"""Single source of "now", so demos and evals can freeze the date with AGENT_TODAY."""

import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

STORE_TZ = ZoneInfo("America/Campo_Grande")


def now() -> datetime:
    frozen = os.getenv("AGENT_TODAY", "").strip()
    if frozen:
        # "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
        parsed = datetime.fromisoformat(frozen)
        if len(frozen) == 10:
            parsed = datetime.combine(parsed.date(), time(10, 0))
        return parsed.replace(tzinfo=STORE_TZ)
    return datetime.now(STORE_TZ)


def today() -> date:
    return now().date()
