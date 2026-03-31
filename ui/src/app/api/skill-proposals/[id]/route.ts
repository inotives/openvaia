import { NextRequest, NextResponse } from "next/server";
import { sql, SCHEMA } from "@/lib/db";

/** GET — get a single proposal */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  try {
    const rows = await sql`
      SELECT p.*,
             s.name AS skill_name, s.content AS current_content
      FROM ${sql(SCHEMA)}.skill_evolution_proposals p
      LEFT JOIN ${sql(SCHEMA)}.skills s ON s.id = p.skill_id
      WHERE p.id = ${Number(id)}
    `;

    if (rows.length === 0) {
      return NextResponse.json({ error: "Proposal not found" }, { status: 404 });
    }

    return NextResponse.json(rows[0]);
  } catch (err) {
    console.error("Failed to fetch proposal:", err);
    return NextResponse.json({ error: "Failed to fetch proposal" }, { status: 500 });
  }
}

/** PATCH — approve or reject a proposal */
export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { status, review_notes, reviewed_by } = await req.json();

  if (!status || !["approved", "rejected"].includes(status)) {
    return NextResponse.json({ error: "status must be 'approved' or 'rejected'" }, { status: 400 });
  }

  try {
    // Update proposal status
    await sql`
      UPDATE ${sql(SCHEMA)}.skill_evolution_proposals
      SET status = ${status},
          review_notes = ${review_notes || null},
          reviewed_by = ${reviewed_by || "admin"},
          reviewed_at = NOW()
      WHERE id = ${Number(id)}
    `;

    // If approved, apply the evolution
    if (status === "approved") {
      const proposal = await sql`
        SELECT * FROM ${sql(SCHEMA)}.skill_evolution_proposals WHERE id = ${Number(id)}
      `;
      const p = proposal[0];

      if (p.evolution_type === "captured" && p.proposed_name) {
        // Create new skill
        const newSkill = await sql`
          INSERT INTO ${sql(SCHEMA)}.skills
            (name, description, content, tags, global, enabled, status, created_by)
          VALUES (${p.proposed_name}, ${p.proposed_description || ""}, ${p.proposed_content},
                  ${p.proposed_tags || []}, false, true, 'active', ${p.proposed_by})
          RETURNING id
        `;
        // Create version record
        await sql`
          INSERT INTO ${sql(SCHEMA)}.skill_versions
            (skill_id, version, origin, generation, change_summary, content_snapshot, is_active, created_by)
          VALUES (${newSkill[0].id}, 1, 'captured', 0, ${p.direction}, ${p.proposed_content}, true, ${p.proposed_by})
        `;
      } else if (p.skill_id && ["fix", "derived"].includes(p.evolution_type)) {
        // Get current version
        const curVersion = await sql`
          SELECT COALESCE(MAX(version), 0) AS max_v, MAX(generation) AS max_gen
          FROM ${sql(SCHEMA)}.skill_versions WHERE skill_id = ${p.skill_id}
        `;
        const newVersion = (curVersion[0].max_v || 0) + 1;
        const newGen = (curVersion[0].max_gen || 0) + 1;

        // Deactivate old versions
        await sql`
          UPDATE ${sql(SCHEMA)}.skill_versions
          SET is_active = false
          WHERE skill_id = ${p.skill_id}
        `;

        // Create new version
        await sql`
          INSERT INTO ${sql(SCHEMA)}.skill_versions
            (skill_id, version, origin, generation, change_summary, content_snapshot, is_active, created_by)
          VALUES (${p.skill_id}, ${newVersion}, ${p.evolution_type}, ${newGen},
                  ${p.direction}, ${p.proposed_content}, true, ${p.proposed_by})
        `;

        // Update skill content
        await sql`
          UPDATE ${sql(SCHEMA)}.skills
          SET content = ${p.proposed_content}, updated_at = NOW()
          WHERE id = ${p.skill_id}
        `;
      }

      // Mark as applied
      await sql`
        UPDATE ${sql(SCHEMA)}.skill_evolution_proposals
        SET status = 'applied'
        WHERE id = ${Number(id)}
      `;
    }

    return NextResponse.json({ ok: true, status });
  } catch (err) {
    console.error("Failed to update proposal:", err);
    return NextResponse.json({ error: "Failed to update proposal" }, { status: 500 });
  }
}
