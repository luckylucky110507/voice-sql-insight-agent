from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


SYSTEM_PROMPT = """
You convert analytics questions into a safe JSON query plan.
Return JSON only.

Allowed output schema:
{
  "metric": "revenue|profit|cost|units|incidents|churn|csat|risk",
  "dimension": "region|product_line|month|risk",
  "mode": "ranking|trend|risk",
  "sort": "desc|asc",
  "filters": {
    "region": "North|South|East|West",
    "product_line": "Alpha|Beta",
    "month": "2025-01-01|2025-02-01|2025-03-01|2025-04-01"
  }
}

Rules:
- Use only the allowed schema, fields, and enum values.
- Never output SQL.
- Never invent columns or tables.
- For trend questions, use dimension=month and mode=trend.
- For anomaly/risk/issues questions, use mode=risk and dimension=risk.
- For "highest/top/best" use sort=desc.
- For "lowest/bottom/worst" use sort=asc.
""".strip()


class LLMPlanner:
    def __init__(self) -> None:
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.api_base_url = os.getenv("LLM_API_BASE_URL", "").strip()
        self.model = os.getenv("LLM_MODEL", "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.api_base_url and self.model)

    def build_plan(self, question: str, context: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "prior_context": context,
                            "schema": {
                                "table": "business_metrics",
                                "dimensions": ["region", "product_line", "month"],
                                "metrics": [
                                    "revenue",
                                    "profit",
                                    "cost",
                                    "units",
                                    "incidents",
                                    "churn",
                                    "csat",
                                    "risk",
                                ],
                            },
                        }
                    ),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.api_base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        content = self._extract_content(response_payload)
        if not content:
            return None

        try:
            plan = json.loads(content)
        except json.JSONDecodeError:
            return None
        return plan if isinstance(plan, dict) else None

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            return "".join(text_parts)
        return ""
