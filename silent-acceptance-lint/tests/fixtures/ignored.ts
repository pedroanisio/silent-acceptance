import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

export async function withReason(): Promise<void> {
  // silent-acceptance-ignore: output is discarded; only latency is measured in this probe
  await client.messages.create({ model: "claude-sonnet-5", max_tokens: 1, messages: [] });
}

export async function withoutReason(): Promise<void> {
  await client.messages.create({ model: "claude-sonnet-5", max_tokens: 1, messages: [] }); // silent-acceptance-ignore
}
