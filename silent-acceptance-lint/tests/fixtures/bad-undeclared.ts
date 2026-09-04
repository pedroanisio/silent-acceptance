import OpenAI from "openai";

const openai = new OpenAI();

export async function classify(text: string): Promise<string> {
  const completion = await openai.chat.completions.create({
    model: "gpt-5",
    messages: [{ role: "user", content: text }],
  });
  // Output flows straight to the caller: silent acceptance.
  return completion.choices[0]?.message.content ?? "";
}
