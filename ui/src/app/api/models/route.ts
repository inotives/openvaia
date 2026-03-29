import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

interface ModelEntry {
  id: string;
  provider: string;
  model: string;
  context_window: number;
  max_tokens: number;
}

/** Simple parser for models.yml — extracts model entries without a YAML library */
function parseModelsYml(content: string): ModelEntry[] {
  const models: ModelEntry[] = [];
  let current: Partial<ModelEntry> | null = null;

  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (line.startsWith("- id:")) {
      if (current?.id) models.push(current as ModelEntry);
      current = { id: line.replace("- id:", "").trim() };
    } else if (current && line.startsWith("provider:")) {
      current.provider = line.replace("provider:", "").trim();
    } else if (current && line.startsWith("model:")) {
      current.model = line.replace("model:", "").trim();
    } else if (current && line.startsWith("context_window:")) {
      current.context_window = parseInt(line.replace("context_window:", "").trim());
    } else if (current && line.startsWith("max_tokens:")) {
      current.max_tokens = parseInt(line.replace("max_tokens:", "").trim());
    }
  }
  if (current?.id) models.push(current as ModelEntry);

  return models;
}

/** GET — list all available models from models.yml */
export async function GET() {
  try {
    const paths = [
      "/app/inotagent/models.yml",
      resolve(process.cwd(), "../inotagent/models.yml"),
    ];

    let content: string | null = null;
    for (const p of paths) {
      if (existsSync(p)) {
        content = readFileSync(p, "utf-8");
        break;
      }
    }

    if (!content) {
      return NextResponse.json({ error: "models.yml not found" }, { status: 404 });
    }

    return NextResponse.json(parseModelsYml(content));
  } catch (err) {
    console.error("Failed to load models:", err);
    return NextResponse.json({ error: "Failed to load models" }, { status: 500 });
  }
}
