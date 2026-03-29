import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await req.json();
    const { prompt, interval_minutes, enabled } = body;

    // Fetch current values first, then merge updates
    const current = await sql`
      SELECT * FROM ${sql(SCHEMA)}.cron_jobs WHERE id = ${Number(id)}
    `;

    if (current.length === 0) {
      return NextResponse.json({ error: "Cron job not found" }, { status: 404 });
    }

    const job = current[0];
    const newPrompt = prompt !== undefined ? prompt : job.prompt;
    const newInterval = interval_minutes !== undefined ? interval_minutes : job.interval_minutes;
    const newEnabled = enabled !== undefined ? enabled : job.enabled;

    const rows = await sql`
      UPDATE ${sql(SCHEMA)}.cron_jobs SET
        prompt = ${newPrompt},
        interval_minutes = ${newInterval},
        enabled = ${newEnabled},
        updated_at = NOW()
      WHERE id = ${Number(id)}
      RETURNING *
    `;

    return NextResponse.json(rows[0]);
  } catch (err) {
    console.error("Failed to update cron job:", err);
    return NextResponse.json({ error: "Failed to update cron job" }, { status: 500 });
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;

    const rows = await sql`
      DELETE FROM ${sql(SCHEMA)}.cron_jobs
      WHERE id = ${Number(id)}
      RETURNING id, name
    `;

    if (rows.length === 0) {
      return NextResponse.json({ error: "Cron job not found" }, { status: 404 });
    }

    return NextResponse.json({ deleted: rows[0] });
  } catch (err) {
    console.error("Failed to delete cron job:", err);
    return NextResponse.json({ error: "Failed to delete cron job" }, { status: 500 });
  }
}
