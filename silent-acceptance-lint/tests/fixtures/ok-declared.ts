import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

/**
 * ⚠ VERIFICATION BOUNDARY — Silent Acceptance specification
 *
 * SILENT_ACCEPTANCE_VERSION: 2.1.0
 * SOLVER_CONFIGURATION_ID: sum-v3 (claude-sonnet-5 / retrieval harness / 8k ctx)
 * VERIFIER_LOCATION: src/verify/summary-schema.ts (separate module, read-only to agents)
 * ACCEPTANCE_AUTHORITY: ci/verdicts (append-only, outside the producer's control domain)
 * TOLERATED_FAILURE_RATE: 0.01
 * OWNER: platform-quality
 * CALIBRATED_ON: 2026-09-03
 *
 * class            | verifier            | evidence      | recall/spec | on reject | status
 * ERR_HALLUCINATION| retrieval crosscheck| source corpus | 0.82 / 0.95 | escalate  | COVERED
 * ERR_OMISSION     | field assertion     | schema        | 0.97 / 0.99 | retry     | COVERED
 * ERR_SCHEMA       | zod parse           | schema        | 1.00 / 1.00 | abstain   | COVERED
 * ERR_TRUNCATION   | -                   | -             | -           | -         | ACCEPTED_RISK: length capped upstream
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
