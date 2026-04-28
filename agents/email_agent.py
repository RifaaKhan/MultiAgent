from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json


def generate_email_content(request_type: str, user: dict, details: str):
    llm = get_flash_model()
    prompt_template = load_prompt("email_agent_prompt.txt")

    prompt = f"""
{prompt_template}

Request Type:
{request_type}

User:
{user}

Details:
{details}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    return {
        "subject": parsed.get("subject", f"{request_type} Notification"),
        "body": parsed.get("body", details),
    }