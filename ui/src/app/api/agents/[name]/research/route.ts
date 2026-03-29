import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — list research reports for an agent */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { searchParams } = req.nextUrl;
  const search = searchParams.get("q");
  const tag = searchParams.get("tag");
  const from = searchParams.get("from");
  const to = searchParams.get("to");

  try {
    const rows = await sql`
      SELECT id, task_key, title, summary, tags, created_at
      FROM ${sql(SCHEMA)}.research_reports
      WHERE agent_name = ${name}
        ${search ? sql`AND title ILIKE ${"%" + search + "%"}` : sql``}
        ${tag ? sql`AND ${tag} = ANY(tags)` : sql``}
        ${from ? sql`AND created_at >= ${from}::date` : sql``}
        ${to ? sql`AND created_at < (${to}::date + interval '1 day')` : sql``}
      ORDER BY created_at DESC
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch research reports:", err);
    return NextResponse.json({ error: "Failed to fetch reports" }, { status: 500 });
  }
}
