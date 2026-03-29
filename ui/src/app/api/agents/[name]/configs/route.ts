import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — list all config key-value pairs for an agent */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const rows = await sql`
      SELECT key, value, source, description, updated_at
      FROM ${sql(SCHEMA)}.agent_configs
      WHERE agent_name = ${name}
      ORDER BY key
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch agent configs:", err);
    return NextResponse.json({ error: "Failed to fetch configs" }, { status: 500 });
  }
}

/** PATCH — update a config value */
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { key, value } = await req.json();

  if (!key || value === undefined) {
    return NextResponse.json({ error: "key and value are required" }, { status: 400 });
  }

  try {
    await sql`
      INSERT INTO ${sql(SCHEMA)}.agent_configs (agent_name, key, value, source, updated_at)
      VALUES (${name}, ${key}, ${value}, 'ui', NOW())
      ON CONFLICT (agent_name, key)
      DO UPDATE SET value = ${value}, source = 'ui', updated_at = NOW()
    `;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to update agent config:", err);
    return NextResponse.json({ error: "Failed to update config" }, { status: 500 });
  }
}
