import json
import re


def extract_json(text: str) -> dict:
    """
    Extract JSON from LLM response safely.
    Handles normal JSON and markdown JSON blocks.
    """
    text = text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            return json.loads(match.group())

        return {
            "action": "unknown",
            "error": "Could not parse LLM response",
            "raw_response": text
        }