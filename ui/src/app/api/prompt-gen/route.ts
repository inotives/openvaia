import { NextRequest, NextResponse } from "next/server";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const SYSTEM_PROMPT = `You are a prompt engineering expert for the OpenVAIA AI agent platform.

Your job: take the user's rough instruction and rewrite it into a clear, structured prompt that an AI agent can execute effectively.

The agents have these capabilities:
- Shell commands, file read/write, browser (web research)
- Task management (task_create, task_update, task_list)
- Memory (memory_store, memory_search)
- Research reports (research_store, research_search)
- Discord/Slack/Telegram messaging
- Git operations (clone, commit, push via shell)

When enhancing a prompt:
1. Clarify the objective — what exactly should the agent deliver?
2. Specify scope — what's in and out of bounds?
3. Define output format — report, code, summary, data?
4. Mention relevant tools if applicable
5. Add success criteria — how does the human know it's done?

Rules:
- Respond in a single pass. Do not ask follow-up questions.
- Return ONLY the enhanced prompt, no commentary or explanation.
- Keep it concise but thorough — aim for 100-300 words.
- Match the complexity to the task — simple tasks get simple prompts.`;

interface ModelInfo {
  id: string;
  provider: string;
  model: string;
  api_key_env?: string;
  base_url?: string;
  max_tokens: number;
}

/** Parse models.yml to get provider details */
function loadModels(): ModelInfo[] {
  const paths = [
    "/app/inotagent/models.yml",
    resolve(process.cwd(), "../inotagent/models.yml"),
  ];

  for (const p of paths) {
    if (existsSync(p)) {
      const content = readFileSync(p, "utf-8");
      const models: ModelInfo[] = [];
      let current: Partial<ModelInfo> | null = null;

      for (const raw of content.split("\n")) {
        const line = raw.trim();
        if (line.startsWith("- id:")) {
          if (current?.id) models.push(current as ModelInfo);
          current = { id: line.replace("- id:", "").trim() };
        } else if (current && line.startsWith("provider:")) {
          current.provider = line.replace("provider:", "").trim();
        } else if (current && line.startsWith("model:")) {
          current.model = line.replace("model:", "").trim();
        } else if (current && line.startsWith("api_key_env:")) {
          const val = line.replace("api_key_env:", "").trim();
          current.api_key_env = val === "null" ? undefined : val;
        } else if (current && line.startsWith("base_url:")) {
          current.base_url = line.replace("base_url:", "").trim();
        } else if (current && line.startsWith("max_tokens:")) {
          current.max_tokens = parseInt(line.replace("max_tokens:", "").trim());
        }
      }
      if (current?.id) models.push(current as ModelInfo);
      return models;
    }
  }
  return [];
}

/** Parse platform.yml for prompt_gen config */
function loadPromptGenConfig(): { default_model: string; fallbacks: string[]; max_tokens: number } {
  const paths = [
    "/app/inotagent/platform.yml",
    resolve(process.cwd(), "../inotagent/platform.yml"),
  ];

  for (const p of paths) {
    if (existsSync(p)) {
      const content = readFileSync(p, "utf-8");
      let inPromptGen = false;
      let inFallbacks = false;
      let defaultModel = "groq-llama-3.3-70b";
      let maxTokens = 1024;
      const fallbacks: string[] = [];

      for (const raw of content.split("\n")) {
        const line = raw.trim();
        if (line === "prompt_gen:") { inPromptGen = true; inFallbacks = false; continue; }
        if (inPromptGen && !line.startsWith("-") && !line.startsWith("#") && line.includes(":") && !line.startsWith("fallbacks")) {
          if (line.startsWith("default_model:")) defaultModel = line.replace("default_model:", "").trim();
          if (line.startsWith("max_tokens:")) maxTokens = parseInt(line.replace("max_tokens:", "").trim());
        }
        if (inPromptGen && line === "fallbacks:") { inFallbacks = true; continue; }
        if (inFallbacks && line.startsWith("- ")) { fallbacks.push(line.replace("- ", "").trim()); continue; }
        if (inFallbacks && !line.startsWith("-") && !line.startsWith("#")) { inFallbacks = false; }
        if (inPromptGen && line !== "" && !line.startsWith(" ") && !line.startsWith("-") && !line.startsWith("#") && line.includes(":") && !["default_model:", "max_tokens:", "fallbacks:"].some(k => line.startsWith(k))) {
          inPromptGen = false;
        }
      }
      return { default_model: defaultModel, fallbacks, max_tokens: maxTokens };
    }
  }
  return { default_model: "nvidia-minimax-2.5", fallbacks: ["nvidia-mistral-large-3"], max_tokens: 1024 };
}

/** Call OpenAI-compatible chat completion with timeout */
async function callLLM(model: ModelInfo, userMessage: string, maxTokens: number): Promise<string> {
  const apiKey = model.api_key_env ? process.env[model.api_key_env] || "" : "";
  const baseUrl = model.base_url?.replace(/\/$/, "") || "";

  console.log(`[prompt-gen] Calling ${model.id} (${model.model}) at ${baseUrl}`);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  try {
    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: model.model,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userMessage },
        ],
        max_tokens: maxTokens,
      }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`LLM call failed (${res.status}): ${text.slice(0, 200)}`);
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content?.trim() || "";
    console.log(`[prompt-gen] ${model.id} responded (${content.length} chars)`);
    return content;
  } finally {
    clearTimeout(timeout);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { instruction, model: requestedModel } = body;

    if (!instruction) {
      return NextResponse.json({ error: "instruction is required" }, { status: 400 });
    }

    const models = loadModels();
    const config = loadPromptGenConfig();

    console.log(`[prompt-gen] Config: default=${config.default_model}, fallbacks=${config.fallbacks}, max_tokens=${config.max_tokens}`);
    console.log(`[prompt-gen] Models loaded: ${models.map(m => `${m.id}(${m.provider},url=${m.base_url},key=${m.api_key_env})`).join(', ')}`);
    console.log(`[prompt-gen] NVIDIA_API_KEY set: ${!!process.env.NVIDIA_API_KEY}`);

    // Build model chain: requested model (if specified) → default → fallbacks
    const chain: string[] = [];
    if (requestedModel) chain.push(requestedModel);
    if (!chain.includes(config.default_model)) chain.push(config.default_model);
    for (const fb of config.fallbacks) {
      if (!chain.includes(fb)) chain.push(fb);
    }

    const modelMap = Object.fromEntries(models.map(m => [m.id, m]));
    let lastError = "";

    for (const modelId of chain) {
      const modelInfo = modelMap[modelId];
      if (!modelInfo) continue;
      // Skip models without API key
      if (modelInfo.api_key_env && !process.env[modelInfo.api_key_env]) continue;

      try {
        const enhanced = await callLLM(modelInfo, instruction, config.max_tokens);
        return NextResponse.json({
          enhanced_prompt: enhanced,
          model_used: modelId,
        });
      } catch (err: any) {
        lastError = err.message || "Unknown error";
        console.warn(`Prompt gen: ${modelId} failed: ${lastError}, trying next`);
      }
    }

    return NextResponse.json(
      { error: `All models failed. Last error: ${lastError}` },
      { status: 502 },
    );
  } catch (err) {
    console.error("Prompt gen error:", err);
    return NextResponse.json({ error: "Failed to generate prompt" }, { status: 500 });
  }
}
