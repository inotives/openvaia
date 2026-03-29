import { NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";
import type { TaskSummaryRow } from "@/lib/types";

export async function GET() {
  try {
    const rows = await sql`
      SELECT
        COALESCE(assigned_to, created_by) AS agent,
        status,
        COUNT(*)::int AS count
      FROM ${sql(SCHEMA)}.tasks
      GROUP BY agent, status
      ORDER BY agent, status
    `;

    // Pivot: group by agent, spread statuses into columns
    const agents = new Map<string, TaskSummaryRow>();
    for (const row of rows) {
      if (!agents.has(row.agent)) {
        agents.set(row.agent, {
          agent: row.agent,
          backlog: 0,
          todo: 0,
          in_progress: 0,
          review: 0,
          done: 0,
          blocked: 0,
        });
      }
      const entry = agents.get(row.agent)!;
      const status = row.status as keyof Omit<TaskSummaryRow, "agent">;
      if (status in entry) {
        entry[status] = row.count;
      }
    }

    return NextResponse.json(Array.from(agents.values()));
  } catch (err) {
    console.error("Failed to fetch task summary:", err);
    return NextResponse.json({ error: "Failed to fetch task summary" }, { status: 500 });
  }
}
