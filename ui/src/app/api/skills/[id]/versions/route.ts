import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — skill version history (lineage) */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  try {
    const rows = await sql`
      SELECT
        sv.id, sv.version, sv.origin, sv.generation,
        sv.parent_version_ids, sv.change_summary,
        sv.is_active, sv.created_by, sv.created_at,
        LENGTH(sv.content_snapshot) AS content_length
      FROM ${sql(SCHEMA)}.skill_versions sv
      WHERE sv.skill_id = ${Number(id)}
      ORDER BY sv.version DESC
    `;

    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch skill versions:", err);
    return NextResponse.json({ error: "Failed to fetch versions" }, { status: 500 });
  }
}
