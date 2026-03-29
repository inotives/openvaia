import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json();

  const allowedFields = ["name", "description", "content", "tags", "global", "enabled", "status"];
  const sets: string[] = [];
  const values: any[] = [];

  for (const field of allowedFields) {
    if (field in body) {
      sets.push(field);
      values.push(body[field]);
    }
  }

  if (!sets.length) {
    return NextResponse.json({ error: "No valid fields" }, { status: 400 });
  }

  try {
    const setClauses = sets.map((f, i) => `${f} = $${i + 2}`).join(", ");
    const query = `
      UPDATE ${SCHEMA}.skills
      SET ${setClauses}, updated_at = NOW()
      WHERE id = $1
      RETURNING *
    `;
    const rows = await sql.unsafe(query, [id, ...values]);
    if (!rows.length) {
      return NextResponse.json({ error: "Skill not found" }, { status: 404 });
    }
    return NextResponse.json(rows[0]);
  } catch (err) {
    console.error("Failed to update skill:", err);
    return NextResponse.json({ error: "Failed to update skill" }, { status: 500 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const rows = await sql.unsafe(
      `DELETE FROM ${SCHEMA}.skills WHERE id = $1 RETURNING id`,
      [id],
    );
    if (!rows.length) {
      return NextResponse.json({ error: "Skill not found" }, { status: 404 });
    }
    return NextResponse.json({ deleted: id });
  } catch (err) {
    console.error("Failed to delete skill:", err);
    return NextResponse.json({ error: "Failed to delete skill" }, { status: 500 });
  }
}
