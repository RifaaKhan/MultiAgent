from pathlib import Path

PROMPT_DIR = Path("prompts")


def load_prompt(prompt_name: str) -> str:
    prompt_path = PROMPT_DIR / prompt_name

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")