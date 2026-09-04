import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

/**
 * ⚠ VERIFICATION BOUNDARY — Silent Acceptance specification
 *
 * SILENT_ACCEPTANCE_VERSION: 2.1.0
 * SOLVER_CONFIGURATION_ID: draft-v1 (claude-sonnet-5 / no tools)
 * ACCEPTANCE_AUTHORITY: ci/verdicts
 * MITIGATION: reviewed by hand before release
 *
 * class            | verifier | evidence | recall/spec | on reject | status
 * ERR_HALLUCINATION| -        | -        | -           | -         | ACCEPTED_RISK: no oracle
 * ERR_SCHEMA       | -        | -        | -           | -         | ACCEPTED_RISK: free text
 */
export async function draft(topic: string): Promise<string> {
  const res = await client.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 512,
    messages: [{ role: "user", content: topic }],
  });
  return res.content[0].type === "text" ? res.content[0].text : "";
}
