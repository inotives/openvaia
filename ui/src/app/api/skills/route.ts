import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET() {
  try {
    const rows = await sql`
      SELECT s.*,
             (SELECT count(*)::int FROM ${sql(SCHEMA)}.agent_skills WHERE skill_id = s.id) AS agent_count
      FROM ${sql(SCHEMA)}.skills s
      ORDER BY s.global DESC, s.name
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch skills:", err);
    return NextResponse.json({ error: "Failed to fetch skills" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, description, content, tags, global: isGlobal } = body;

    if (!name || !content) {
      return NextResponse.json({ error: "name and content are required" }, { status: 400 });
    }

    const rows = await sql`
      INSERT INTO ${sql(SCHEMA)}.skills (name, description, content, tags, global)
      VALUES (${name}, ${description || ""}, ${content}, ${tags || []}, ${isGlobal || false})
      RETURNING *
    `;
    return NextResponse.json(rows[0], { status: 201 });
  } catch (err) {
    console.error("Failed to create skill:", err);
    return NextResponse.json({ error: "Failed to create skill" }, { status: 500 });
  }
}
