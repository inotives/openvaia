import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const rows = await sql`
      SELECT id, repo_url, name AS repo_name, description, assigned_by, created_at
      FROM ${sql(SCHEMA)}.agent_repos
      WHERE agent_name = ${name}
      ORDER BY created_at DESC
    `;
    return NextResponse.json(rows);
  } catch (err) {
    console.error("Failed to fetch repos:", err);
    return NextResponse.json({ error: "Failed to fetch repos" }, { status: 500 });
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const { repo_url, repo_name, assigned_by } = await req.json();

    if (!repo_url || !repo_name) {
      return NextResponse.json({ error: "repo_url and repo_name are required" }, { status: 400 });
    }

    const rows = await sql`
      INSERT INTO ${sql(SCHEMA)}.agent_repos (agent_name, repo_url, name, assigned_by)
      VALUES (${name}, ${repo_url}, ${repo_name}, ${assigned_by || null})
      RETURNING id, repo_url, name AS repo_name, assigned_by, created_at
    `;
    return NextResponse.json(rows[0], { status: 201 });
  } catch (err: any) {
    if (err?.code === "23505") {
      return NextResponse.json({ error: "Repo already assigned to this agent" }, { status: 409 });
    }
    console.error("Failed to add repo:", err);
    return NextResponse.json({ error: "Failed to add repo" }, { status: 500 });
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const { id, repo_url, repo_name, assigned_by } = await req.json();

    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }

    const rows = await sql`
      UPDATE ${sql(SCHEMA)}.agent_repos
      SET repo_url = ${repo_url}, name = ${repo_name}, assigned_by = ${assigned_by || null}
      WHERE id = ${id} AND agent_name = ${name}
      RETURNING id, repo_url, name AS repo_name, assigned_by, created_at
    `;

    if (rows.length === 0) {
      return NextResponse.json({ error: "Repo not found" }, { status: 404 });
    }
    return NextResponse.json(rows[0]);
  } catch (err: any) {
    if (err?.code === "23505") {
      return NextResponse.json({ error: "Repo URL already assigned to this agent" }, { status: 409 });
    }
    console.error("Failed to update repo:", err);
    return NextResponse.json({ error: "Failed to update repo" }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  try {
    const { id } = await req.json();

    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }

    const rows = await sql`
      DELETE FROM ${sql(SCHEMA)}.agent_repos
      WHERE id = ${id} AND agent_name = ${name}
      RETURNING id
    `;

    if (rows.length === 0) {
      return NextResponse.json({ error: "Repo not found" }, { status: 404 });
    }
    return NextResponse.json({ success: true });
  } catch (err) {
    console.error("Failed to delete repo:", err);
    return NextResponse.json({ error: "Failed to delete repo" }, { status: 500 });
  }
}
