import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const status = searchParams.get("status");
  const assignedTo = searchParams.get("assigned_to");
  const priority = searchParams.get("priority");
  const createdBy = searchParams.get("created_by");
  const search = searchParams.get("q");
  const tag = searchParams.get("tag");
  const from = searchParams.get("from");
  const to = searchParams.get("to");

  try {
    const rows = await sql`
      SELECT key, title, description, status, priority,
             assigned_to, created_by, result, tags,
             created_at, updated_at
      FROM ${sql(SCHEMA)}.tasks
      WHERE 1=1
        ${status ? sql`AND status = ${status}` : sql``}
        ${assignedTo === "unassigned" ? sql`AND assigned_to IS NULL` : assignedTo ? sql`AND assigned_to = ${assignedTo}` : sql``}
        ${priority ? sql`AND priority = ${priority}` : sql``}
        ${createdBy ? sql`AND created_by = ${createdBy}` : sql``}
        ${tag ? sql`AND ${tag} = ANY(tags)` : sql``}
        ${search ? sql`AND (title ILIKE ${"%" + search + "%"} OR description ILIKE ${"%" + search + "%"})` : sql``}
        ${from ? sql`AND created_at >= ${from}::date` : sql``}
        ${to ? sql`AND created_at < (${to}::date + interval '1 day')` : sql``}
      ORDER BY
        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
        created_at DESC
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch tasks:", err);
    return NextResponse.json({ error: "Failed to fetch tasks" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { title, description, priority, assigned_to, created_by, tags } = body;

    if (!title || !created_by) {
      return NextResponse.json({ error: "title and created_by are required" }, { status: 400 });
    }

    // Generate key from created_by prefix
    const prefix = (created_by as string).slice(0, 3).toUpperCase();
    const seqRows = await sql`SELECT nextval(${SCHEMA + ".task_key_seq"}) AS seq`;
    const key = `${prefix}-${String(seqRows[0].seq).padStart(3, "0")}`;

    const rows = await sql`
      INSERT INTO ${sql(SCHEMA)}.tasks (key, title, description, status, priority, assigned_to, created_by, tags)
      VALUES (
        ${key},
        ${title},
        ${description || null},
        ${assigned_to ? "todo" : "backlog"},
        ${priority || "medium"},
        ${assigned_to || null},
        ${created_by},
        ${tags || []}
      )
      RETURNING key, title, status, priority, assigned_to, created_by, tags, created_at
    `;
    return NextResponse.json(rows[0], { status: 201 });
  } catch (err) {
    console.error("Failed to create task:", err);
    return NextResponse.json({ error: "Failed to create task" }, { status: 500 });
  }
}
