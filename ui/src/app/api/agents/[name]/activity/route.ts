import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — get agent's most recent user message (any channel) + busy status */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;

  try {
    // Get most recent user message across all channels
    const msgs = await sql`
      SELECT content, channel_type, created_at
      FROM ${sql(SCHEMA)}.conversations
      WHERE agent_name = ${name}
        AND role = 'user'
        AND content IS NOT NULL
        AND content != ''
      ORDER BY created_at DESC
      LIMIT 1
    `;

    // Get busy status from latest health check
    const status = await sql`
      SELECT details
      FROM ${sql(SCHEMA)}.agent_status
      WHERE agent_name = ${name}
      ORDER BY checked_at DESC
      LIMIT 1
    `;

    const isBusy = status[0]?.details?.is_busy || false;
    const lastMessage = msgs[0]?.content || "";
    const channel = msgs[0]?.channel_type || "";

    return NextResponse.json({ isBusy, lastMessage, channel });
  } catch (err) {
    console.error("Failed to fetch agent activity:", err);
    return NextResponse.json({ error: "Failed to fetch activity" }, { status: 500 });
  }
}
