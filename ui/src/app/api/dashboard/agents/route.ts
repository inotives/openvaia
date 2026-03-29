import { NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET() {
  try {
    const rows = await sql`
      SELECT a.name, a.role,
             CASE WHEN a.last_seen > NOW() - INTERVAL '2 minutes' THEN a.status ELSE 'offline' END AS status,
             a.last_seen,
             CASE WHEN a.last_seen > NOW() - INTERVAL '2 minutes' THEN s.healthy ELSE false END AS healthy,
             s.details, s.checked_at,
             COALESCE(sk.skill_count, 0)::int AS skill_count
      FROM ${sql(SCHEMA)}.agents a
      LEFT JOIN LATERAL (
          SELECT healthy, details, checked_at
          FROM ${sql(SCHEMA)}.agent_status
          WHERE agent_name = a.name
          ORDER BY checked_at DESC LIMIT 1
      ) s ON true
      LEFT JOIN LATERAL (
          SELECT count(DISTINCT sub.name)::int AS skill_count FROM (
              SELECT sk2.name FROM ${sql(SCHEMA)}.skills sk2
              WHERE sk2.global = true AND sk2.enabled = true
              UNION
              SELECT sk3.name FROM ${sql(SCHEMA)}.skills sk3
              JOIN ${sql(SCHEMA)}.agent_skills ags ON ags.skill_id = sk3.id
              WHERE ags.agent_name = a.name AND sk3.enabled = true
          ) sub
      ) sk ON true
      ORDER BY a.name
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch agents:", err);
    return NextResponse.json({ error: "Failed to fetch agents" }, { status: 500 });
  }
}
