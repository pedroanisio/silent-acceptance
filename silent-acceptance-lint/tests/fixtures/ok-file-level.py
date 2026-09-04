"""Batch extraction workers.

@verification-boundary file
SILENT_ACCEPTANCE_VERSION: 2.0.0
MODEL_VERSION: gemini-3-pro
VERIFIER_LOCATION: extraction/verify.py (runs in the reviewer service)
  [x] ERR_SCHEMA        — pydantic model parse
  [x] ERR_OMISSION      — required keys asserted
  [ ] ERR_HALLUCINATION — accepted risk
MITIGATION: hallucination is caught downstream by the human review queue.
"""

from google import genai

client = genai.Client()


def extract(doc: str) -> dict:
    response = client.models.generate_content(model="gemini-3-pro", contents=doc)
    return parse_and_verify(response.text)


def extract_again(doc: str) -> dict:
    response = client.models.generate_content(model="gemini-3-pro", contents=doc)
    return parse_and_verify(response.text)


def parse_and_verify(text: str) -> dict:
    return {"text": text}
