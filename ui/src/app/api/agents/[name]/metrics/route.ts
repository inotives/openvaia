import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** Run a query, returning fallback on error (e.g. missing table). */
async function safe(query: Promise<any>, fallback: any[] = []): Promise<any[]> {
  try {
    return await query;
  } catch {
    return fallback;
  }
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;

  try {
    const [
      agentRow,
      tasksByStatus,
      tasksByPriority,
      messageCounts,
      memoryCounts,
      researchCount,
      conversationCount,
      repoCount,
      healthHistory,
      activityTimeline,
      completionHeatmap,
      skillCount,
      systemPromptChars,
      tokenUsage,
      tokenTimeline,
    ] = await Promise.all([
      safe(sql`
        SELECT role FROM ${sql(SCHEMA)}.agents WHERE name = ${name}
      `, []),
      safe(sql`
        SELECT status, count(*)::int AS count
        FROM ${sql(SCHEMA)}.tasks
        WHERE assigned_to = ${name}
        GROUP BY status
      `, []),
      safe(sql`
        SELECT priority, status, count(*)::int AS count
        FROM ${sql(SCHEMA)}.tasks
        WHERE assigned_to = ${name}
        GROUP BY priority, status
      `, []),
      safe(sql`
        SELECT channel_type, count(*)::int AS count
        FROM ${sql(SCHEMA)}.conversations
        WHERE agent_name = ${name}
        GROUP BY channel_type
      `, []),
      safe(sql`
        SELECT tier, count(*)::int AS count
        FROM ${sql(SCHEMA)}.memories
        WHERE agent_name = ${name}
        GROUP BY tier
      `, []),
      safe(sql`
        SELECT count(*)::int AS count
        FROM ${sql(SCHEMA)}.research_reports
        WHERE agent_name = ${name}
      `, []),
      safe(sql`
        SELECT count(DISTINCT conversation_id)::int AS count
        FROM ${sql(SCHEMA)}.conversations
        WHERE agent_name = ${name}
      `, []),
      safe(sql`
        SELECT count(*)::int AS count
        FROM ${sql(SCHEMA)}.agent_repos
        WHERE agent_name = ${name}
      `, []),
      safe(sql`
        SELECT checked_at, details
        FROM ${sql(SCHEMA)}.agent_status
        WHERE agent_name = ${name}
          AND checked_at > now() - interval '24 hours'
        ORDER BY checked_at
      `, []),
      safe(sql`
        SELECT date, tasks_created, tasks_completed, messages_sent FROM (
          SELECT d::date AS date,
            (SELECT count(*) FROM ${sql(SCHEMA)}.tasks
             WHERE assigned_to = ${name} AND created_at::date = d::date)::int AS tasks_created,
            (SELECT count(*) FROM ${sql(SCHEMA)}.tasks
             WHERE assigned_to = ${name} AND status = 'done' AND updated_at::date = d::date)::int AS tasks_completed,
            (SELECT count(*) FROM ${sql(SCHEMA)}.messages
             WHERE from_agent = ${name} AND created_at::date = d::date)::int AS messages_sent
          FROM generate_series(now() - interval '30 days', now(), '1 day') AS d
        ) sub
        ORDER BY date
      `, []),
      // Task completion heatmap (last 6 months)
      safe(sql`
        SELECT updated_at::date AS date, count(*)::int AS count
        FROM ${sql(SCHEMA)}.tasks
        WHERE assigned_to = ${name}
          AND status = 'done'
          AND updated_at > now() - interval '6 months'
        GROUP BY updated_at::date
        ORDER BY date
      `, []),
      safe(sql`
        SELECT count(DISTINCT sub.name)::int AS count FROM (
          SELECT s.name FROM ${sql(SCHEMA)}.skills s
          WHERE s.global = true AND s.enabled = true
          UNION
          SELECT s.name FROM ${sql(SCHEMA)}.skills s
          JOIN ${sql(SCHEMA)}.agent_skills ags ON ags.skill_id = s.id
          WHERE ags.agent_name = ${name} AND s.enabled = true
        ) sub
      `, []),
      // System prompt token count (calculated by inotagent at boot)
      safe(sql`
        SELECT value FROM ${sql(SCHEMA)}.agent_configs
        WHERE agent_name = ${name} AND key = 'system_prompt_tokens'
      `, []),
      // Token usage from conversation metadata (last 24h)
      safe(sql`
        SELECT
          COALESCE(SUM((metadata->>'input_tokens')::int), 0)::int AS total_input,
          COALESCE(SUM((metadata->>'output_tokens')::int), 0)::int AS total_output,
          COALESCE(SUM((metadata->>'total_tokens')::int), 0)::int AS total_tokens
        FROM ${sql(SCHEMA)}.conversations
        WHERE agent_name = ${name}
          AND role = 'assistant'
          AND metadata->>'total_tokens' IS NOT NULL
          AND created_at > now() - interval '24 hours'
      `, []),
      // Daily token usage (last 30 days)
      safe(sql`
        SELECT d::date AS date,
          COALESCE(SUM((c.metadata->>'input_tokens')::int), 0)::int AS input_tokens,
          COALESCE(SUM((c.metadata->>'output_tokens')::int), 0)::int AS output_tokens
        FROM generate_series(now() - interval '30 days', now(), '1 day') AS d
        LEFT JOIN ${sql(SCHEMA)}.conversations c
          ON c.agent_name = ${name}
          AND c.role = 'assistant'
          AND c.metadata->>'total_tokens' IS NOT NULL
          AND c.created_at::date = d::date
        GROUP BY d::date
        ORDER BY date
      `, []),
    ]);

    // Build activity radar data (for circular barplot)
    const statusMap: Record<string, number> = {};
    for (const r of tasksByStatus) statusMap[r.status] = r.count;

    const totalTasks = Object.values(statusMap).reduce((a: number, b: number) => a + b, 0);
    const convoByChannel: Record<string, number> = {};
    for (const r of messageCounts) convoByChannel[r.channel_type] = r.count;
    const totalMemories = memoryCounts.reduce((a: number, r: any) => a + r.count, 0);

    const radar = [
      { category: "Tasks", value: totalTasks, color: "#1677ff" },
      { category: "Done", value: statusMap["done"] || 0, color: "#52c41a" },
      { category: "In Progress", value: statusMap["in_progress"] || 0, color: "#faad14" },
      { category: "Discord", value: convoByChannel["discord"] || 0, color: "#5865F2" },
      { category: "Slack", value: convoByChannel["slack"] || 0, color: "#4A154B" },
      { category: "Web Chat", value: convoByChannel["web"] || 0, color: "#722ed1" },
      { category: "Memories", value: totalMemories, color: "#eb2f96" },
      { category: "Research", value: researchCount[0]?.count || 0, color: "#13c2c2" },
      { category: "Conversations", value: conversationCount[0]?.count || 0, color: "#faad14" },
      { category: "Repos", value: repoCount[0]?.count || 0, color: "#2f54eb" },
      { category: "Skills", value: skillCount[0]?.count || 0, color: "#fa541c" },
    ];

    const usage = tokenUsage[0] || { total_input: 0, total_output: 0, total_tokens: 0 };

    return NextResponse.json({
      role: agentRow[0]?.role || "",
      radar,
      tasksByStatus: statusMap,
      tasksByPriority,
      memoryCounts,
      researchCount: researchCount[0]?.count || 0,
      conversationCount: conversationCount[0]?.count || 0,
      repoCount: repoCount[0]?.count || 0,
      healthHistory,
      activityTimeline,
      completionHeatmap,
      tokenUsage: {
        input: usage.total_input,
        output: usage.total_output,
        total: usage.total_tokens,
      },
      systemPromptTokens: parseInt(systemPromptChars[0]?.value || "0", 10),
      tokenTimeline,
    });
  } catch (err) {
    console.error("Failed to fetch agent metrics:", err);
    return NextResponse.json({ error: "Failed to fetch agent metrics" }, { status: 500 });
  }
}
