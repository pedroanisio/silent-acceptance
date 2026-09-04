import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

/**
 * ⚠ VERIFICATION BOUNDARY — Silent Acceptance specification
 *
 * SILENT_ACCEPTANCE_VERSION: 2.0.0
 * MODEL_VERSION: claude-sonnet-5
 * VERIFIER_LOCATION: src/verify/summary-schema.ts (separate module, read-only to agents)
 *
 * ERROR CLASSES NOT COVERED BY THIS BOUNDARY:
 *   [x] ERR_HALLUCINATION   — covered: retrieval cross-check
 *   [x] ERR_OMISSION        — covered: required-field assertion
 *   [x] ERR_SCHEMA          — covered: zod parse
 *   [ ] ERR_TRUNCATION      — accepted risk
 *   [ ] ERR_SYCOPHANCY      — accepted risk
 *   [ ] ERR_INSTRUCTION     — accepted risk
 *   [ ] ERR_CALIBRATION     — accepted risk
 *   [ ] ERR_SEMANTIC        — accepted risk
 *   [ ] ERR_REASONING       — accepted risk
 *
 * MITIGATION: unchecked classes are accepted for this low-stakes summary path.
 */
export async function summarize(text: string): Promise<string> {
  const msg = await client.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 200,
    messages: [{ role: "user", content: `Summarize: ${text}` }],
  });
  return verifySummary(msg);
}

declare function verifySummary(msg: unknown): string;
