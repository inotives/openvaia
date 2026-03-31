import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — skill quality metrics across all agents */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  try {
    const rows = await sql`
      SELECT
        sm.agent_name,
        sm.times_selected,
        sm.times_applied,
        sm.times_completed,
        sm.times_fallback,
        sm.last_applied_at,
        CASE WHEN sm.times_selected > 0
          THEN ROUND(sm.times_completed::numeric / sm.times_selected, 3)
          ELSE 0 END AS effective_rate,
        CASE WHEN sm.times_selected > 0
          THEN ROUND(sm.times_fallback::numeric / sm.times_selected, 3)
          ELSE 0 END AS fallback_rate
      FROM ${sql(SCHEMA)}.skill_metrics sm
      WHERE sm.skill_id = ${Number(id)}
      ORDER BY sm.times_selected DESC
    `;

    // Also get totals
    const totals = await sql`
      SELECT
        SUM(times_selected) AS total_selected,
        SUM(times_applied) AS total_applied,
        SUM(times_completed) AS total_completed,
        SUM(times_fallback) AS total_fallback
      FROM ${sql(SCHEMA)}.skill_metrics
      WHERE skill_id = ${Number(id)}
    `;

    return NextResponse.json({
      skill_id: Number(id),
      totals: totals[0] || { total_selected: 0, total_applied: 0, total_completed: 0, total_fallback: 0 },
      by_agent: rows,
    });
  } catch (err) {
    console.error("Failed to fetch skill metrics:", err);
    return NextResponse.json({ error: "Failed to fetch metrics" }, { status: 500 });
  }
}
