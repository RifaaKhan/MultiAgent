from datetime import datetime
from zoneinfo import ZoneInfo

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


def get_current_date() -> str:
    """
    Gets today's date in Asia/Kolkata timezone.
    No external API is used.
    """
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")


def format_my_leaves(leaves):
    if isinstance(leaves, str):
        return leaves

    if not leaves:
        return "No leave requests found."

    lines = ["My Leave Requests:\n"]

    for leave in leaves:
        lines.append(
            f"Request ID: {leave['request_id']}\n"
            f"Leave Type: {leave['leave_type']}\n"
            f"Dates: {leave['start_date']} to {leave['end_date']}\n"
            f"Status: {leave['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def should_auto_set_one_day_leave(latest_message: str) -> bool:
    text = f" {latest_message.lower()} "

    one_day_patterns = [
        " on ",
        "for one day",
        "for a day",
        "one day off",
        "today",
        "tomorrow",
        "day after tomorrow",
    ]

    return any(pattern in text for pattern in one_day_patterns)


def run_hr_agent(user: dict, message: str):
    latest_message = get_latest_user_message(message)
    latest_lower = latest_message.lower()
    current_date = get_current_date()

    # STRICT leave balance detection
    balance_patterns = [
        "my leave balance",
        "remaining leaves",
        "how many leaves do i have",
        "my remaining leaves",
    ]

    if any(pattern in latest_lower for pattern in balance_patterns):
        return get_leave_balance_report(user_id=user["user_id"])

    # STRICT leave status detection
    leave_status_patterns = [
        "my leave requests",
        "my applied leaves",
        "my leaves",
        "leave history",
        "check my leave status",
    ]

    if any(pattern in latest_lower for pattern in leave_status_patterns):
        return format_my_leaves(check_leave_status(user["user_id"]))

    llm = get_pro_model()
    prompt_template = load_prompt("hr_agent_prompt.txt")

    prompt = f"""
{prompt_template}

Current Date:
{current_date}

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

    # SAFETY FIX FOR MULTI-TURN LEAVE FLOW
    ongoing_leave_context = (
        "missing leave details" in message.lower()
        or "i want a leave" in message.lower()
        or "apply leave" in message.lower()
    )

    if action == "get_leave_balance" and ongoing_leave_context:
        action = "apply_leave"

    # LEAVE BALANCE
    if action == "get_leave_balance":
        return get_leave_balance_report(
            user_id=user["user_id"],
            leave_type=parsed.get("leave_type")
        )

    # APPLY LEAVE
    if action == "apply_leave":

        # AUTO ONE-DAY LEAVE
        if (
            parsed.get("start_date")
            and not parsed.get("end_date")
            and should_auto_set_one_day_leave(latest_message)
        ):
            parsed["end_date"] = parsed["start_date"]

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

    # LEAVE STATUS
    if action == "check_leave_status":
        return format_my_leaves(check_leave_status(user["user_id"]))

    # CANCEL LEAVE
    if action == "cancel_leave":
        if not parsed.get("request_id"):
            return "Please provide the leave request ID to cancel."

        return cancel_leave(
            user_id=user["user_id"],
            request_id=parsed["request_id"],
        )

    return "I could not understand the HR request clearly."