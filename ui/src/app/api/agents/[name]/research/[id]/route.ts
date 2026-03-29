import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — get full research report by id */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string; id: string }> },
) {
  const { name, id } = await params;

  try {
    const rows = await sql`
      SELECT id, task_key, title, summary, body, tags, created_at
      FROM ${sql(SCHEMA)}.research_reports
      WHERE agent_name = ${name} AND id = ${Number(id)}
    `;

    if (rows.length === 0) {
      return NextResponse.json({ error: "Report not found" }, { status: 404 });
    }

    return NextResponse.json(rows[0]);
  } catch (err) {
    console.error("Failed to fetch report:", err);
    return NextResponse.json({ error: "Failed to fetch report" }, { status: 500 });
  }
}
