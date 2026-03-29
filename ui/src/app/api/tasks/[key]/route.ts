import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;
  const body = await req.json();

  const allowedFields = ["status", "priority", "assigned_to", "title", "description", "result", "tags"];
  const updates: string[] = [];
  const values: any[] = [];

  for (const field of allowedFields) {
    if (field in body) {
      updates.push(field);
      values.push(body[field]);
    }
  }

  if (!updates.length) {
    return NextResponse.json({ error: "No valid fields to update" }, { status: 400 });
  }

  try {
    // Build dynamic SET clause
    const setClauses = updates.map((f, i) => `${f} = $${i + 2}`).join(", ");
    const query = `
      UPDATE ${SCHEMA}.tasks
      SET ${setClauses}, updated_at = NOW()
      WHERE key = $1
      RETURNING key, title, status, priority, assigned_to, created_by, tags, result, updated_at
    `;

    const rows = await sql.unsafe(query, [key, ...values]);
    if (!rows.length) {
      return NextResponse.json({ error: "Task not found" }, { status: 404 });
    }
    return NextResponse.json(rows[0]);
  } catch (err) {
    console.error("Failed to update task:", err);
    return NextResponse.json({ error: "Failed to update task" }, { status: 500 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ key: string }> },
) {
  const { key } = await params;
  try {
    const rows = await sql.unsafe(
      `DELETE FROM ${SCHEMA}.tasks WHERE key = $1 RETURNING key`,
      [key],
    );
    if (!rows.length) {
      return NextResponse.json({ error: "Task not found" }, { status: 404 });
    }
    return NextResponse.json({ deleted: key });
  } catch (err) {
    console.error("Failed to delete task:", err);
    return NextResponse.json({ error: "Failed to delete task" }, { status: 500 });
  }
}
