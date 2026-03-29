import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const tier = req.nextUrl.searchParams.get("tier");
  const tag = req.nextUrl.searchParams.get("tag");
  const search = req.nextUrl.searchParams.get("q");
  const from = req.nextUrl.searchParams.get("from");
  const to = req.nextUrl.searchParams.get("to");
  const limit = Math.min(parseInt(req.nextUrl.searchParams.get("limit") || "100", 10) || 100, 500);

  try {
    const rows = await sql`
      SELECT id, content, tags, tier, created_at
      FROM ${sql(SCHEMA)}.memories
      WHERE agent_name = ${name}
        ${tier ? sql`AND tier = ${tier}` : sql``}
        ${tag ? sql`AND ${tag} = ANY(tags)` : sql``}
        ${search ? sql`AND to_tsvector('english', content) @@ plainto_tsquery('english', ${search})` : sql``}
        ${from ? sql`AND created_at >= ${from}::date` : sql``}
        ${to ? sql`AND created_at < (${to}::date + interval '1 day')` : sql``}
      ORDER BY created_at DESC
      LIMIT ${limit}
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch memories:", err);
    return NextResponse.json({ error: "Failed to fetch memories" }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { id } = await req.json();

  try {
    await sql`
      DELETE FROM ${sql(SCHEMA)}.memories
      WHERE id = ${id} AND agent_name = ${name}
    `;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to delete memory:", err);
    return NextResponse.json({ error: "Failed to delete memory" }, { status: 500 });
  }
}
