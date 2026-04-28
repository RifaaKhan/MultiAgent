from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import approve_request


def run_approval_agent(user: dict, message: str):
    llm = get_flash_model()
    prompt_template = load_prompt("approval_agent_prompt.txt")

    prompt = f"""
{prompt_template}

Approver User:
{user}

Message:
{message}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    request_type = parsed.get("request_type")
    request_id = parsed.get("request_id")
    decision = parsed.get("decision")

    if not request_type or not request_id or not decision:
        return "Please provide request type, request ID, and approval decision."

    return approve_request(
        approver_id=user["user_id"],
        request_type=request_type,
        request_id=request_id,
        decision=decision,
    )