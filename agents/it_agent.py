from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import (
    create_ticket,
    get_ticket_status,
    create_asset_request,
)


def run_it_agent(user: dict, message: str):
    llm = get_flash_model()
    prompt_template = load_prompt("it_agent_prompt.txt")

    prompt = f"""
{prompt_template}

User:
{user}

Message:
{message}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    action = parsed.get("action", "unknown")

    if action == "create_ticket":
        if not parsed.get("issue_type"):
            return "Please provide the IT issue type."

        return create_ticket(
            user_id=user["user_id"],
            issue_type=parsed["issue_type"],
            description=parsed.get("description", message),
            priority=parsed.get("priority") or "Medium",
        )

    if action == "get_ticket_status":
        return get_ticket_status(
            user_id=user["user_id"],
            role=user["role"],
        )

    if action == "create_asset_request":
        if not parsed.get("asset_type"):
            return "Please provide the asset type you need."

        return create_asset_request(
            user_id=user["user_id"],
            asset_type=parsed["asset_type"],
            reason=parsed.get("reason", message),
        )

    return "I could not understand the IT request clearly."