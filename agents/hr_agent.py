from llm_config import get_pro_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import (
    apply_leave,
    get_leave_balance_report,
    check_leave_status,
    cancel_leave,
)


def get_latest_user_message(message: str) -> str:
    if "Latest user message:" in message:
        return message.split("Latest user message:")[-1].strip()
    return message.strip()


def format_my_leaves(leaves):
    if isinstance(leaves, str):
        return leaves

    if not leaves:
        return "No leave requests found."

    lines = ["My Leave Requests:"]

    for leave in leaves:
        lines.append(
            f"{leave['request_id']} | "
            f"Type: {leave['leave_type']} | "
            f"Dates: {leave['start_date']} to {leave['end_date']} | "
            f"Status: {leave['status']}"
        )

    return "\n".join(lines)


def run_hr_agent(user: dict, message: str):
    latest_message = get_latest_user_message(message)
    latest_lower = latest_message.lower()

    if "balance" in latest_lower or "remaining" in latest_lower:
        return get_leave_balance_report(user_id=user["user_id"])

    if (
        "leave request" in latest_lower
        or "leave requests" in latest_lower
        or "applied leave" in latest_lower
        or "applied leaves" in latest_lower
        or "leave history" in latest_lower
        or "my leaves" in latest_lower
    ):
        return format_my_leaves(check_leave_status(user["user_id"]))

    llm = get_pro_model()
    prompt_template = load_prompt("hr_agent_prompt.txt")

    prompt = f"""
{prompt_template}

User:
{user}

Latest User Message:
{latest_message}

Conversation Context:
{message}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    action = parsed.get("action", "unknown")

    if action == "get_leave_balance":
        return get_leave_balance_report(
            user_id=user["user_id"],
            leave_type=parsed.get("leave_type")
        )

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
        return format_my_leaves(check_leave_status(user["user_id"]))

    if action == "cancel_leave":
        if not parsed.get("request_id"):
            return "Please provide the leave request ID to cancel."

        return cancel_leave(
            user_id=user["user_id"],
            request_id=parsed["request_id"],
        )

    return "I could not understand the HR request clearly."