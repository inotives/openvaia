import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — list skill evolution proposals (filterable by status) */
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const status = searchParams.get("status");

  try {
    const rows = await sql`
      SELECT p.*,
             s.name AS skill_name
      FROM ${sql(SCHEMA)}.skill_evolution_proposals p
      LEFT JOIN ${sql(SCHEMA)}.skills s ON s.id = p.skill_id
      WHERE 1=1
        ${status ? sql`AND p.status = ${status}` : sql``}
      ORDER BY p.created_at DESC
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch proposals:", err);
    return NextResponse.json({ error: "Failed to fetch proposals" }, { status: 500 });
  }
}
