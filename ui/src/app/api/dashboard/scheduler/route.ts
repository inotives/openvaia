import { NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

interface SchedulerInfo {
  agent: string;
  status: string;
  is_busy: boolean;
  uptime_seconds: number;
  last_heartbeat: string | null;
  tasks: SchedulerTask[];
}

interface SchedulerTask {
  name: string;
  type: "heartbeat" | "cron";
  interval: string;
  enabled: boolean;
  description: string;
}

export async function GET() {
  try {
    // Get agent statuses with details
    const agents = await sql`
      SELECT a.name,
             CASE WHEN a.last_seen > NOW() - INTERVAL '2 minutes' THEN a.status ELSE 'offline' END AS status,
             s.details, s.checked_at
      FROM ${sql(SCHEMA)}.agents a
      LEFT JOIN LATERAL (
          SELECT details, checked_at
          FROM ${sql(SCHEMA)}.agent_status
          WHERE agent_name = a.name
          ORDER BY checked_at DESC LIMIT 1
      ) s ON true
      ORDER BY a.name
    `;

    // Get heartbeat config
    const heartbeatConfig = await sql`
      SELECT value FROM ${sql(SCHEMA)}.config
      WHERE key = 'heartbeat.interval_seconds'
    `;
    const heartbeatInterval = heartbeatConfig[0]?.value || "60";

    // Get cron jobs from DB
    const cronJobs = await sql`
      SELECT * FROM ${sql(SCHEMA)}.cron_jobs
      WHERE enabled = true
      ORDER BY COALESCE(agent_name, ''), name
    `;

    const result: SchedulerInfo[] = agents.map((agent: any) => {
      const details = agent.details || {};

      // Heartbeat is always-on
      const tasks: SchedulerTask[] = [
        {
          name: "heartbeat",
          type: "heartbeat",
          interval: `${heartbeatInterval}s`,
          enabled: true,
          description: "Health reporting, task/mission detection, daily pruning",
        },
      ];

      // Add cron jobs for this agent (agent-specific + global)
      const agentJobs = cronJobs.filter(
        (j: any) => j.agent_name === agent.name || j.agent_name === null
      );

      // Deduplicate: agent-specific overrides global (same name)
      const seen = new Set<string>();
      for (const job of agentJobs) {
        if (seen.has(job.name)) continue;
        seen.add(job.name);
        const minutes = job.interval_minutes;
        const interval = minutes >= 60 ? `${Math.round(minutes / 60)}h` : `${minutes}m`;
        tasks.push({
          name: job.name,
          type: "cron",
          interval,
          enabled: job.enabled,
          description: job.prompt.length > 80 ? job.prompt.slice(0, 77) + "..." : job.prompt,
        });
      }

      return {
        agent: agent.name,
        status: agent.status,
        is_busy: details.is_busy ?? false,
        uptime_seconds: details.uptime_seconds ?? 0,
        last_heartbeat: agent.checked_at,
        tasks,
      };
    });

    return NextResponse.json(result);
  } catch (err) {
    console.error("Failed to fetch scheduler info:", err);
    return NextResponse.json({ error: "Failed to fetch scheduler info" }, { status: 500 });
  }
}
