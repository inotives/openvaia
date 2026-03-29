import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — list all platform config entries */
export async function GET() {
  try {
    const rows = await sql`
      SELECT key, value, description, updated_at
      FROM ${sql(SCHEMA)}.config
      ORDER BY key
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch platform config:", err);
    return NextResponse.json({ error: "Failed to fetch config" }, { status: 500 });
  }
}

/** PUT — upsert a config entry */
export async function PUT(req: NextRequest) {
  const { key, value, description } = await req.json();

  if (!key || value === undefined) {
    return NextResponse.json({ error: "key and value are required" }, { status: 400 });
  }

  try {
    await sql`
      INSERT INTO ${sql(SCHEMA)}.config (key, value, description, updated_at)
      VALUES (${key}, ${value}, ${description || null}, NOW())
      ON CONFLICT (key)
      DO UPDATE SET value = ${value}, description = COALESCE(${description || null}, ${sql(SCHEMA)}.config.description), updated_at = NOW()
    `;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to upsert platform config:", err);
    return NextResponse.json({ error: "Failed to save config" }, { status: 500 });
  }
}

/** DELETE — remove a config entry */
export async function DELETE(req: NextRequest) {
  const { key } = await req.json();

  if (!key) {
    return NextResponse.json({ error: "key is required" }, { status: 400 });
  }

  try {
    const rows = await sql`
      DELETE FROM ${sql(SCHEMA)}.config
      WHERE key = ${key}
      RETURNING key
    `;
    if (!rows.length) {
      return NextResponse.json({ error: "Key not found" }, { status: 404 });
    }
    return NextResponse.json({ deleted: key });
  } catch (err) {
    console.error("Failed to delete platform config:", err);
    return NextResponse.json({ error: "Failed to delete config" }, { status: 500 });
  }
}
