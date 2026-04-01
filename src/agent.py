from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from src.data_setup import open_connection, parameter_placeholder
from src.llm_planner import LLMPlanner


TABLE_NAME = "business_metrics"
REGIONS = ["north", "south", "east", "west"]
PRODUCTS = ["alpha", "beta"]
ALLOWED_FILTERS = {
    "region": {"North", "South", "East", "West"},
    "product_line": {"Alpha", "Beta"},
    "month": {"2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"},
}
ALLOWED_DIMENSIONS = {"region", "product_line", "month", "risk"}
ALLOWED_MODES = {"ranking", "trend", "risk"}
ALLOWED_SORTS = {"desc", "asc"}
METRIC_CONFIG = {
    "revenue": {"sql": "SUM(revenue)", "label": "revenue", "format": "currency"},
    "profit": {"sql": "SUM(revenue - cost)", "label": "profit", "format": "currency"},
    "cost": {"sql": "SUM(cost)", "label": "cost", "format": "currency"},
    "units": {"sql": "SUM(units_sold)", "label": "units sold", "format": "integer"},
    "incidents": {"sql": "SUM(incident_count)", "label": "incidents", "format": "integer"},
    "churn": {"sql": "AVG(customer_churn)", "label": "customer churn", "format": "percent"},
    "csat": {"sql": "AVG(csat)", "label": "customer satisfaction", "format": "decimal"},
}
MONTH_ALIASES = {
    "january": "2025-01-01",
    "february": "2025-02-01",
    "march": "2025-03-01",
    "april": "2025-04-01",
}


def format_value(value: float | int | None, style: str) -> str:
    if value is None:
        return "n/a"
    if style == "currency":
        return f"${value:,.0f}"
    if style == "integer":
        return f"{int(round(value)):,}"
    if style == "percent":
        return f"{value:.1f}%"
    return f"{value:.2f}"


@dataclass
class ConversationContext:
    metric: str = "revenue"
    dimension: str = "region"
    filters: dict[str, str] = field(default_factory=dict)
    last_sql: str = ""
    last_title: str = ""


class VoiceSQLAgent:
    def __init__(self, db_config: dict[str, Any]):
        self.db_config = db_config
        self.sessions: dict[str, ConversationContext] = {}
        self.llm_planner = LLMPlanner()

    def handle_query(self, session_id: str, question: str) -> dict[str, Any]:
        context = self.sessions.setdefault(session_id, ConversationContext())
        plan = self._build_plan(question, context)
        rows = self._run_query(plan["sql"], plan["params"])
        response = self._build_response(question, plan, rows, context)
        context.metric = plan["metric"]
        context.dimension = plan["dimension"]
        context.filters = plan["filters"]
        context.last_sql = plan["sql"]
        context.last_title = response["title"]
        return {
            "question": question,
            "title": response["title"],
            "summary": response["summary"],
            "spoken_response": response["spoken_response"],
            "insights": response["insights"],
            "sql": plan["sql"],
            "params": plan["params"],
            "table": rows,
            "chart": {
                "label_key": plan["dimension_key"],
                "value_key": "value",
                "format": METRIC_CONFIG[plan["metric"]]["format"],
            },
            "context": {
                "metric": context.metric,
                "dimension": context.dimension,
                "filters": context.filters,
            },
            "planner": plan.get("planner", "rules"),
        }

    def _build_plan(self, question: str, context: ConversationContext) -> dict[str, Any]:
        llm_plan = self._try_llm_plan(question, context)
        if llm_plan is not None:
            return llm_plan

        normalized = question.lower().strip()
        metric = self._detect_metric(normalized, context)
        dimension = self._detect_dimension(normalized, context)
        filters = self._detect_filters(normalized, context)

        if any(term in normalized for term in ["risk", "risks", "anomaly", "anomalies", "issue", "issues"]):
            return self._risk_plan(metric, filters, planner="rules")
        if any(term in normalized for term in ["trend", "over time", "monthly", "month wise"]):
            return self._trend_plan(metric, filters, planner="rules")
        if any(term in normalized for term in ["top", "highest", "best", "leading"]):
            return self._ranking_plan(metric, dimension, filters, descending=True, planner="rules")
        if any(term in normalized for term in ["bottom", "lowest", "worst"]):
            return self._ranking_plan(metric, dimension, filters, descending=False, planner="rules")
        return self._ranking_plan(metric, dimension, filters, descending=True, planner="rules")

    def _detect_metric(self, normalized: str, context: ConversationContext) -> str:
        if any(term in normalized for term in ["what about", "follow up", "same", "that", "those", "and "]):
            return context.metric
        if "profit" in normalized or "margin" in normalized:
            return "profit"
        if "cost" in normalized or "expense" in normalized:
            return "cost"
        if "unit" in normalized or "volume" in normalized:
            return "units"
        if "incident" in normalized or "ticket" in normalized:
            return "incidents"
        if "churn" in normalized or "retention" in normalized:
            return "churn"
        if "csat" in normalized or "satisfaction" in normalized or "customer score" in normalized:
            return "csat"
        return "revenue"

    def _detect_dimension(self, normalized: str, context: ConversationContext) -> str:
        if any(term in normalized for term in ["what about", "follow up", "same", "those", "them"]):
            return context.dimension
        if "product" in normalized or "alpha" in normalized or "beta" in normalized:
            return "product_line"
        if "month" in normalized or "trend" in normalized or "time" in normalized:
            return "month"
        return "region"

    def _detect_filters(self, normalized: str, context: ConversationContext) -> dict[str, str]:
        filters: dict[str, str] = {}
        for region in REGIONS:
            if region in normalized:
                filters["region"] = region.title()
        for product in PRODUCTS:
            if product in normalized:
                filters["product_line"] = product.title()
        for name, iso_date in MONTH_ALIASES.items():
            if name in normalized:
                filters["month"] = iso_date

        if any(term in normalized for term in ["what about", "follow up", "same", "that region", "that product", "there", "and "]):
            merged = context.filters.copy()
            merged.update(filters)
            return merged
        return filters

    def _ranking_plan(
        self,
        metric: str,
        dimension: str,
        filters: dict[str, str],
        descending: bool,
        planner: str,
    ) -> dict[str, Any]:
        where_clause, params = self._build_where(filters, exclude_dimension=dimension)
        order = "DESC" if descending else "ASC"
        sql = f"""
            SELECT {dimension} AS label,
                   ROUND({METRIC_CONFIG[metric]["sql"]}, 2) AS value
            FROM {TABLE_NAME}
            {where_clause}
            GROUP BY {dimension}
            ORDER BY value {order}
            LIMIT 6
        """
        return {
            "metric": metric,
            "dimension": dimension,
            "dimension_key": "label",
            "filters": filters,
            "sql": self._compact_sql(sql),
            "params": params,
            "planner": planner,
        }

    def _trend_plan(self, metric: str, filters: dict[str, str], planner: str) -> dict[str, Any]:
        where_clause, params = self._build_where(filters, exclude_dimension="month")
        sql = f"""
            SELECT month AS label,
                   ROUND({METRIC_CONFIG[metric]["sql"]}, 2) AS value
            FROM {TABLE_NAME}
            {where_clause}
            GROUP BY month
            ORDER BY month ASC
        """
        return {
            "metric": metric,
            "dimension": "month",
            "dimension_key": "label",
            "filters": filters,
            "sql": self._compact_sql(sql),
            "params": params,
            "planner": planner,
        }

    def _risk_plan(self, metric: str, filters: dict[str, str], planner: str) -> dict[str, Any]:
        where_clause, params = self._build_where(filters)
        label_sql = self._risk_label_sql()
        sql = f"""
            SELECT {label_sql} AS label,
                   ROUND(
                       ((customer_churn * 220) + (incident_count * 18) - (csat * 7) + ((cost / revenue) * 100)),
                       2
                   ) AS value
            FROM {TABLE_NAME}
            {where_clause}
            ORDER BY value DESC
            LIMIT 8
        """
        return {
            "metric": metric,
            "dimension": "risk",
            "dimension_key": "label",
            "filters": filters,
            "sql": self._compact_sql(sql),
            "params": params,
            "planner": planner,
        }

    def _risk_label_sql(self) -> str:
        if self.db_config["backend"] == "mysql":
            return "CONCAT(month, ' / ', region, ' / ', product_line)"
        return "month || ' / ' || region || ' / ' || product_line"

    def _try_llm_plan(self, question: str, context: ConversationContext) -> dict[str, Any] | None:
        payload = self.llm_planner.build_plan(
            question,
            {
                "metric": context.metric,
                "dimension": context.dimension,
                "filters": context.filters,
            },
        )
        if payload is None:
            return None

        metric = payload.get("metric")
        dimension = payload.get("dimension")
        mode = payload.get("mode")
        sort = payload.get("sort", "desc")
        filters = payload.get("filters", {})

        if metric not in METRIC_CONFIG:
            return None
        if dimension not in ALLOWED_DIMENSIONS:
            return None
        if mode not in ALLOWED_MODES:
            return None
        if sort not in ALLOWED_SORTS:
            return None
        if not isinstance(filters, dict):
            return None

        safe_filters: dict[str, str] = {}
        for key, value in filters.items():
            if key not in ALLOWED_FILTERS:
                return None
            if value not in ALLOWED_FILTERS[key]:
                return None
            safe_filters[key] = value

        if mode == "risk":
            return self._risk_plan(metric, safe_filters, planner="llm")
        if mode == "trend":
            return self._trend_plan(metric, safe_filters, planner="llm")
        return self._ranking_plan(
            metric,
            dimension,
            safe_filters,
            descending=(sort == "desc"),
            planner="llm",
        )

    def _build_where(self, filters: dict[str, str], exclude_dimension: str | None = None) -> tuple[str, list[str]]:
        clauses = []
        params: list[str] = []
        placeholder = parameter_placeholder(self.db_config)
        for key, value in filters.items():
            if key == exclude_dimension:
                continue
            clauses.append(f"{key} = {placeholder}")
            params.append(value)
        if not clauses:
            return "", params
        return "WHERE " + " AND ".join(clauses), params

    def _run_query(self, sql: str, params: list[str]) -> list[dict[str, Any]]:
        with open_connection(self.db_config) as connection:
            if self.db_config["backend"] == "sqlite":
                connection.row_factory = sqlite3.Row
                rows = connection.execute(sql, params).fetchall()
                return [dict(row) for row in rows]
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())

    def _build_response(
        self,
        question: str,
        plan: dict[str, Any],
        rows: list[dict[str, Any]],
        context: ConversationContext,
    ) -> dict[str, Any]:
        metric_info = METRIC_CONFIG[plan["metric"]]
        metric_label = metric_info["label"]
        title = f"{metric_label.title()} analysis"
        if not rows:
            message = "I could not find matching records for that request."
            return {
                "title": title,
                "summary": message,
                "spoken_response": message,
                "insights": ["Try asking about a specific region, product, or month."],
            }

        top_row = rows[0]
        bottom_row = rows[-1]
        top_value = format_value(top_row["value"], metric_info["format"])
        bottom_value = format_value(bottom_row["value"], metric_info["format"])

        if plan["dimension"] == "month":
            direction = "upward" if rows[-1]["value"] >= rows[0]["value"] else "downward"
            ending_value = format_value(rows[-1]["value"], metric_info["format"])
            summary = (
                f"{metric_label.title()} shows a {direction} trend from "
                f"{rows[0]['label']} to {rows[-1]['label']}, ending at {ending_value}."
            )
            insights = [
                f"Latest month in the result set: {rows[-1]['label']} at {format_value(rows[-1]['value'], metric_info['format'])}.",
                f"Starting month baseline: {rows[0]['label']} at {format_value(rows[0]['value'], metric_info['format'])}.",
            ]
        elif plan["dimension"] == "risk":
            summary = (
                f"The highest current risk signal is {top_row['label']} with a composite risk score of {top_value}."
            )
            insights = [
                f"Top risk hotspot: {top_row['label']} ({top_value}).",
                f"Lowest risk result in this slice: {bottom_row['label']} ({bottom_value}).",
                "Risk score blends churn, incidents, customer satisfaction, and cost pressure.",
            ]
        else:
            summary = (
                f"{top_row['label']} leads for {metric_label} at {top_value}, while "
                f"{bottom_row['label']} is lowest at {bottom_value}."
            )
            insights = [
                f"Leader: {top_row['label']} with {top_value}.",
                f"Lowest performer in this result: {bottom_row['label']} with {bottom_value}.",
            ]

        if context.last_sql and re.search(r"\b(same|follow up|what about|and)\b", question.lower()):
            insights.append("Follow-up context was reused from the prior question where possible.")

        spoken_response = " ".join([summary] + insights[:2])
        return {
            "title": title,
            "summary": summary,
            "spoken_response": spoken_response,
            "insights": insights,
        }

    @staticmethod
    def _compact_sql(sql: str) -> str:
        return re.sub(r"\s+", " ", sql).strip()
