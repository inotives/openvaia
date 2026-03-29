import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — resolved skills for an agent (global + equipped, with override). */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const rows = await sql`
      SELECT DISTINCT ON (s.name)
        s.id, s.name, s.description, s.content, s.tags, s.global, s.enabled,
        COALESCE(ags.priority, 1000) AS priority,
        CASE WHEN ags.agent_name IS NOT NULL THEN true ELSE false END AS equipped
      FROM ${sql(SCHEMA)}.skills s
      LEFT JOIN ${sql(SCHEMA)}.agent_skills ags
        ON ags.skill_id = s.id AND ags.agent_name = ${name}
      WHERE s.enabled = true
        AND (s.global = true OR ags.agent_name IS NOT NULL)
      ORDER BY s.name, equipped DESC, priority ASC
    `;
    // Re-sort by priority for display
    const sorted = [...rows].sort((a: any, b: any) => a.priority - b.priority);
    return NextResponse.json(sorted);
  } catch (err) {
    console.error("Failed to fetch agent skills:", err);
    return NextResponse.json({ error: "Failed to fetch agent skills" }, { status: 500 });
  }
}

/** POST — equip a skill to an agent. */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { skill_id, priority } = await req.json();

  if (!skill_id) {
    return NextResponse.json({ error: "skill_id is required" }, { status: 400 });
  }

  try {
    await sql`
      INSERT INTO ${sql(SCHEMA)}.agent_skills (agent_name, skill_id, priority)
      VALUES (${name}, ${skill_id}, ${priority || 0})
      ON CONFLICT (agent_name, skill_id) DO UPDATE SET priority = ${priority || 0}
    `;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to equip skill:", err);
    return NextResponse.json({ error: "Failed to equip skill" }, { status: 500 });
  }
}

/** DELETE — unequip a skill from an agent. */
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { skill_id } = await req.json();

  try {
    await sql`
      DELETE FROM ${sql(SCHEMA)}.agent_skills
      WHERE agent_name = ${name} AND skill_id = ${skill_id}
    `;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to unequip skill:", err);
    return NextResponse.json({ error: "Failed to unequip skill" }, { status: 500 });
  }
}
