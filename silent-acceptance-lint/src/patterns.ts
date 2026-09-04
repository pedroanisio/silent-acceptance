/**
 * Default call-site patterns and boundary markers.
 *
 * A *call site* is a line of source that invokes an LLM through a known SDK
 * method. A *boundary marker* is text in a comment that declares a verification
 * boundary (Silent Acceptance spec §10.1) or refers to one.
 *
 * The pattern list is deliberately conservative: it matches method names that
 * only LLM SDKs use. Generic verbs such as `invoke(` or `complete(` are not
 * included because they would flood ordinary code with false positives; add them
 * per project through a config file (see README).
 */

export interface CallPattern {
  /** Stable identifier, used in JSON output. */
  id: string;
  /** Human-readable provider or SDK name. */
  provider: string;
  /** Regular expression tested against one source line at a time. */
  regex: RegExp;
}

export const DEFAULT_CALL_PATTERNS: readonly CallPattern[] = [
  { id: "anthropic.messages", provider: "Anthropic SDK", regex: /\.messages\.(create|stream|parse)\s*\(/ },
  { id: "openai.chat", provider: "OpenAI SDK", regex: /\.chat\.completions\.(create|parse|stream)\s*\(/ },
  { id: "openai.responses", provider: "OpenAI SDK", regex: /\.responses\.(create|parse|stream)\s*\(/ },
  { id: "openai.completions", provider: "OpenAI SDK (legacy)", regex: /(?<!\.chat)\.completions\.create\s*\(/ },
  { id: "google.generate", provider: "Google GenAI SDK", regex: /\.(generate_content|generateContent|generateContentStream|generate_content_stream)\s*\(/ },
  { id: "vercel.ai", provider: "Vercel AI SDK", regex: /\b(generateText|generateObject|streamText|streamObject)\s*\(/ },
  { id: "bedrock.converse", provider: "AWS Bedrock", regex: /\b(ConverseCommand|ConverseStreamCommand|InvokeModelCommand|InvokeModelWithResponseStreamCommand)\s*\(|\.(converse|converse_stream|invoke_model)\s*\(/ },
  { id: "ollama", provider: "Ollama", regex: /\bollama\.(chat|generate)\s*\(/ },
  { id: "mistral", provider: "Mistral SDK", regex: /\.chat\.(complete|stream)\s*\(/ },
  { id: "cohere", provider: "Cohere SDK", regex: /\bcohere\w*\.(chat|generate)\s*\(/ },
];

/** Text in a comment that declares (or names) a verification boundary. */
export const BOUNDARY_MARKERS: readonly RegExp[] = [
  /SILENT_ACCEPTANCE_VERSION\s*:/,
  /PALS_LAW_VERSION\s*:/, // v1.x spelling, still honored
  /@verification-boundary\b/,
  /VERIFICATION_BOUNDARY\s*:/,
];

/** A file-level declaration covers every call site in the file. */
export const FILE_LEVEL_MARKER = /(@verification-boundary\s+file\b|SCOPE\s*:\s*file\b|scope\s*[:=]\s*["']?file["']?)/;

/** `silent-acceptance-ignore: <reason>` excuses the call site on that line or the next. */
export const IGNORE_MARKER = /silent-acceptance-ignore(?:\s*:\s*(.*))?/;

/** Lines that are comments in the supported languages; call sites here are not counted. */
export const COMMENT_LINE = /^\s*(\/\/|\/\*|\*|#)/;

export const DEFAULT_EXTENSIONS: readonly string[] = [
  ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".py",
];

export const SKIP_DIRS: ReadonlySet<string> = new Set([
  "node_modules", ".git", "dist", "build", "out", ".venv", "venv",
  "__pycache__", ".next", ".turbo", "coverage", ".silent-acceptance",
]);

/** How many lines above a call site a declaration may sit and still cover it. */
export const DEFAULT_WINDOW = 80;

/** How many lines of a file are searched for a file-level declaration. */
export const FILE_LEVEL_SCAN_LINES = 40;

/** How many lines after a marker belong to its declaration block. */
export const DECLARATION_BLOCK_LINES = 80;
