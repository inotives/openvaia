import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** POST — request agent restart via DB flag (picked up by heartbeat within 60s) */
export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;

  try {
    await sql`
      INSERT INTO ${sql(SCHEMA)}.agent_configs (agent_name, key, value, source, updated_at)
      VALUES (${name}, 'restart_requested', 'true', 'ui', NOW())
      ON CONFLICT (agent_name, key)
      DO UPDATE SET value = 'true', source = 'ui', updated_at = NOW()
    `;
    return NextResponse.json({ ok: true, message: `Restart requested for ${name}. Will take effect within 60s.` });
  } catch (err) {
    console.error("Failed to request restart:", err);
    return NextResponse.json({ error: "Failed to request restart" }, { status: 500 });
  }
}
