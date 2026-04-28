from llm_config import get_pro_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import (
    apply_leave,
    get_leave_balance,
    check_leave_status,
    cancel_leave,
)


def run_hr_agent(user: dict, message: str):
    llm = get_pro_model()
    prompt_template = load_prompt("hr_agent_prompt.txt")

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

    if action == "get_leave_balance":
        return get_leave_balance(user["user_id"])

    if action == "apply_leave":
        required = ["leave_type", "start_date", "end_date"]

        missing = [field for field in required if not parsed.get(field)]

        if missing:
            return f"Please provide missing leave details: {', '.join(missing)}."

        return apply_leave(
            user_id=user["user_id"],
            leave_type=parsed["leave_type"].lower(),
            start_date=parsed["start_date"],
            end_date=parsed["end_date"],
            reason=parsed.get("reason", "Not specified"),
        )

    if action == "check_leave_status":
        return check_leave_status(user["user_id"])

    if action == "cancel_leave":
        if not parsed.get("request_id"):
            return "Please provide the leave request ID to cancel."

        return cancel_leave(
            user_id=user["user_id"],
            request_id=parsed["request_id"],
        )

    return "I could not understand the HR request clearly."