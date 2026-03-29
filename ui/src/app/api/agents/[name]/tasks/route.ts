import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { searchParams } = req.nextUrl;
  const status = searchParams.get("status");
  const priority = searchParams.get("priority");
  const search = searchParams.get("q");
  const tag = searchParams.get("tag");
  const from = searchParams.get("from");
  const to = searchParams.get("to");

  try {
    const rows = await sql`
      SELECT key, title, description, status, priority, assigned_to, created_by,
             result, tags, parent_task_id, created_at, updated_at
      FROM ${sql(SCHEMA)}.tasks
      WHERE (assigned_to = ${name} OR created_by = ${name})
        ${status ? sql`AND status = ${status}` : sql``}
        ${priority ? sql`AND priority = ${priority}` : sql``}
        ${tag ? sql`AND ${tag} = ANY(tags)` : sql``}
        ${search ? sql`AND (title ILIKE ${"%" + search + "%"} OR description ILIKE ${"%" + search + "%"})` : sql``}
        ${from ? sql`AND created_at >= ${from}::date` : sql``}
        ${to ? sql`AND created_at < (${to}::date + interval '1 day')` : sql``}
      ORDER BY updated_at DESC
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch agent tasks:", err);
    return NextResponse.json({ error: "Failed to fetch tasks" }, { status: 500 });
  }
}
