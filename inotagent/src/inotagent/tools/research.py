"""Research tools — store and search research reports via Postgres."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

RESEARCH_STORE_TOOL = {
    "name": "research_store",
    "description": (
        "Save a research report to the database. "
        "Reports are permanent and searchable by any agent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Report title"},
            "summary": {
                "type": "string",
                "description": "Key findings (3-5 bullet points). This is what gets posted to Discord.",
            },
            "body": {"type": "string", "description": "Full markdown report"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags for search (e.g. 'defi', 'coingecko', 'yield')",
            },
            "task_key": {
                "type": "string",
                "description": "Related task key (e.g. 'INO-001')",
            },
        },
        "required": ["title", "summary", "body"],
    },
}

RESEARCH_SEARCH_TOOL = {
    "name": "research_search",
    "description": (
        "Search past research reports by keywords and/or tags. "
        "Returns summaries — use research_get for the full report."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword search"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by topic tags",
            },
        },
    },
}

RESEARCH_GET_TOOL = {
    "name": "research_get",
    "description": "Get the full body of a research report by ID.",
    "input_schema": {
        "type": "object",
        "properties": {
            "report_id": {"type": "integer", "description": "Report ID from research_search results"},
        },
        "required": ["report_id"],
    },
}

RESEARCH_TOOLS = [RESEARCH_STORE_TOOL, RESEARCH_SEARCH_TOOL, RESEARCH_GET_TOOL]

_DB_NOT_CONNECTED = "Error: Database not connected. Research tools require a running Postgres instance."


class ResearchTools:
    """Research report tool handlers backed by async Postgres."""

    def __init__(self, agent_name: str, db_available: bool = False) -> None:
        self.agent_name = agent_name
        self.db_available = db_available

    async def research_store(
        self,
        title: str,
        summary: str,
        body: str,
        tags: list[str] | None = None,
        task_key: str | None = None,
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.research import store_report
        report_id = await store_report(
            self.agent_name, title, summary, body, tags=tags, task_key=task_key,
        )
        return f"Research report saved (id={report_id}): {title}"

    async def research_search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.research import search_reports
        results = await search_reports(
            agent_name=None, query=query, tags=tags,
        )

        if not results:
            return "No research reports found."

        lines = []
        for r in results:
            tag_str = ", ".join(r["tags"]) if r["tags"] else "none"
            date_str = r["created_at"].strftime("%Y-%m-%d")
            task = r["task_key"] or "-"
            lines.append(
                f"[id={r['id']}] {r['title']} | by={r['agent_name']} task={task} "
                f"date={date_str} tags={tag_str}\n  {r['summary']}"
            )
        return "\n---\n".join(lines)

    async def research_get(self, report_id: int) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.research import get_report
        report = await get_report(report_id)
        if not report:
            return f"Error: Report {report_id} not found."

        tag_str = ", ".join(report["tags"]) if report["tags"] else "none"
        return (
            f"# {report['title']}\n"
            f"**Date**: {report['created_at'].strftime('%Y-%m-%d')} | "
            f"**Task**: {report['task_key'] or '-'} | "
            f"**By**: {report['agent_name']} | **Tags**: {tag_str}\n\n"
            f"## Summary\n{report['summary']}\n\n"
            f"{report['body']}"
        )
