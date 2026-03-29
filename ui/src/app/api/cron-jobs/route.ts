import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET(req: NextRequest) {
  try {
    const agent = req.nextUrl.searchParams.get("agent");

    const rows = agent
      ? await sql`
          SELECT * FROM ${sql(SCHEMA)}.cron_jobs
          WHERE agent_name = ${agent} OR agent_name IS NULL
          ORDER BY COALESCE(agent_name, ''), name
        `
      : await sql`
          SELECT * FROM ${sql(SCHEMA)}.cron_jobs
          ORDER BY COALESCE(agent_name, ''), name
        `;

    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch cron jobs:", err);
    return NextResponse.json({ error: "Failed to fetch cron jobs" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { agent_name, name, prompt, interval_minutes = 30, enabled = true } = body;

    if (!name || !prompt) {
      return NextResponse.json({ error: "name and prompt are required" }, { status: 400 });
    }

    // Check if job already exists (matching the COALESCE-based unique index)
    const existing = await sql`
      SELECT id FROM ${sql(SCHEMA)}.cron_jobs
      WHERE COALESCE(agent_name, '') = COALESCE(${agent_name || null}::text, '')
        AND name = ${name}
    `;

    let rows;
    if (existing.length > 0) {
      rows = await sql`
        UPDATE ${sql(SCHEMA)}.cron_jobs SET
          prompt = ${prompt},
          interval_minutes = ${interval_minutes},
          enabled = ${enabled},
          updated_at = NOW()
        WHERE id = ${existing[0].id}
        RETURNING *
      `;
    } else {
      rows = await sql`
        INSERT INTO ${sql(SCHEMA)}.cron_jobs (agent_name, name, prompt, interval_minutes, enabled)
        VALUES (${agent_name || null}, ${name}, ${prompt}, ${interval_minutes}, ${enabled})
        RETURNING *
      `;
    }

    return NextResponse.json(rows[0], { status: 201 });
  } catch (err) {
    console.error("Failed to create cron job:", err);
    return NextResponse.json({ error: "Failed to create cron job" }, { status: 500 });
  }
}
