import { generateText } from "ai";

/**
 * VERIFICATION BOUNDARY
 * SILENT_ACCEPTANCE_VERSION: 2.0.0
 * MODEL_VERSION: <model identifier and version pinned at declaration>
 *
 * ERROR CLASSES NOT COVERED BY THIS BOUNDARY:
 *   [ ] ERR_HALLUCINATION
 *   [ ] ERR_OMISSION
 *   [ ] ERR_SCHEMA
 *   [ ] ERR_TRUNCATION
 *   [ ] ERR_SYCOPHANCY
 *   [ ] ERR_INSTRUCTION
 *   [ ] ERR_CALIBRATION
 *   [ ] ERR_SEMANTIC
 *   [ ] ERR_REASONING
 *
 * MITIGATION: <for every unchecked class, either the downstream boundary that covers it or an accepted-risk note>
 */
export async function draft(prompt: string): Promise<string> {
  const { text } = await generateText({ model: "any", prompt });
  return text;
}
