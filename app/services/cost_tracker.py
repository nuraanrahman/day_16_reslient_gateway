import logging
from datetime import date

logger = logging.getLogger(__name__)

DAILY_LIMIT = 50_000


class CostTracker:
    def __init__(self):
        self.usage = {}

    def record_usage(self, user_id: str, tokens: int):
        today = date.today()
        if user_id not in self.usage or self.usage[user_id]["date"] != today:
            self.usage[user_id] = {"tokens": 0, "date": today}
        self.usage[user_id]["tokens"] += tokens
        logger.info("cost_recorded", extra={
            "event": "cost_recorded",
            "user_id": user_id,
            "tokens_added": tokens,
            "tokens_today": self.usage[user_id]["tokens"],
        })

    def get_usage(self, user_id: str) -> int:
        today = date.today()
        if user_id not in self.usage or self.usage[user_id]["date"] != today:
            return 0
        return self.usage[user_id]["tokens"]

    def is_over_budget(self, user_id: str) -> bool:
        return self.get_usage(user_id) >= DAILY_LIMIT
