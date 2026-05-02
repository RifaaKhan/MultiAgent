import json
import re


def extract_json(text: str) -> dict:
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return {
                    "action": "unknown",
                    "error": "Invalid JSON from LLM",
                    "raw_response": text,
                }

        return {
            "action": "unknown",
            "error": "Could not parse LLM response",
            "raw_response": text,
        }