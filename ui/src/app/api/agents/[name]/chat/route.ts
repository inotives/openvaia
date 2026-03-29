import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — poll conversation history + agent busy status */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const session = req.nextUrl.searchParams.get("session");
  if (!session) {
    return NextResponse.json({ error: "session param required" }, { status: 400 });
  }

  const conversationId = `web-${name}-${session}`;

  try {
    // Fetch conversation messages (user + non-empty assistant only, skip tool calls)
    const messages = await sql`
      SELECT role, content, created_at
      FROM ${sql(SCHEMA)}.conversations
      WHERE conversation_id = ${conversationId}
        AND role IN ('user', 'assistant')
        AND (role = 'user' OR (content IS NOT NULL AND content != ''))
      ORDER BY created_at ASC
    `;

    // Check if there are unprocessed user messages (agent hasn't responded yet)
    const pending = await sql`
      SELECT COUNT(*) AS count
      FROM ${sql(SCHEMA)}.conversations
      WHERE conversation_id = ${conversationId}
        AND channel_type = 'web'
        AND role = 'user'
        AND processed_at IS NULL
    `;

    // Check agent busy status from latest health record
    const health = await sql`
      SELECT details
      FROM ${sql(SCHEMA)}.agent_status
      WHERE agent_name = ${name}
      ORDER BY checked_at DESC
      LIMIT 1
    `;

    const isBusy = health[0]?.details?.is_busy ?? false;
    const hasPending = Number(pending[0]?.count ?? 0) > 0;

    return NextResponse.json({
      messages,
      is_busy: isBusy,
      has_pending: hasPending,
    });
  } catch (err) {
    console.error("Failed to fetch chat:", err);
    return NextResponse.json({ error: "Failed to fetch chat" }, { status: 500 });
  }
}

/** POST — send a message (write to conversations, agent picks up via heartbeat) */
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const { message, session } = await req.json();

  if (!message || typeof message !== "string" || !message.trim()) {
    return NextResponse.json({ error: "Message is required" }, { status: 400 });
  }
  if (!session) {
    return NextResponse.json({ error: "session is required" }, { status: 400 });
  }

  const conversationId = `web-${name}-${session}`;

  try {
    await sql`
      INSERT INTO ${sql(SCHEMA)}.conversations
        (conversation_id, agent_name, role, content, channel_type)
      VALUES (${conversationId}, ${name}, 'user', ${message.trim()}, 'web')
    `;

    return NextResponse.json({ success: true, conversation_id: conversationId });
  } catch (err) {
    console.error("Failed to send message:", err);
    return NextResponse.json({ error: "Failed to send message" }, { status: 500 });
  }
}
