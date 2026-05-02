import time
from collections import defaultdict
from typing import Callable, Any

from tools import save_log

REQUEST_HISTORY = defaultdict(list)


def rate_limit_check(user_id: str, limit: int = 20, window_seconds: int = 60) -> tuple[bool, str]:
    """
    Simple in-memory rate limiter.
    Allows each user only limited requests per time window.
    """
    now = time.time()

    REQUEST_HISTORY[user_id] = [
        timestamp for timestamp in REQUEST_HISTORY[user_id]
        if now - timestamp < window_seconds
    ]

    if len(REQUEST_HISTORY[user_id]) >= limit:
        return False, "Rate limit exceeded. Please try again after a minute."

    REQUEST_HISTORY[user_id].append(now)
    return True, "Allowed"


def retry_llm_call(callable_fn: Callable, max_retries: int = 2, delay_seconds: int = 3) -> Any:
    """
    Retry wrapper for temporary LLM failures.
    Returns a safe error instead of crashing the whole graph.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return callable_fn()
        except Exception as error:
            last_error = error
            error_text = str(error)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                raise RuntimeError("LLM quota exceeded. Please try again later.")

            if attempt < max_retries:
                time.sleep(delay_seconds)

    raise RuntimeError(f"LLM call failed: {last_error}")


def validate_role_before_tool(user: dict, intent: str) -> tuple[bool, str]:
    """
    RBAC check before calling any agent/tool.
    """
    role = user.get("role")

    employee_actions = [
        "policy_question",
        "apply_leave",
        "leave_balance",
        "leave_status",
        "cancel_leave",
        "create_ticket",
        "ticket_status",
        "asset_request",
        "unknown",
        "capabilities",
    ]

    permissions = {
        "Employee": employee_actions,

        "Manager": employee_actions + [
            "approval",
            "show_pending_leaves",
            "show_employees",
            "view_records",
            "analytics",
        ],

        "HR Team": employee_actions + [
            "approval",
            "show_pending_leaves",
            "show_employees",
            "view_records",
            "analytics",
        ],

        "IT Team": employee_actions + [
            "view_records",
            "update_ticket",
            "analytics",
        ],

        "Admin": employee_actions + [
            "add_employee",
            "show_employees",
            "view_records",
            "analytics",
            "email",
        ],
    }

    allowed_intents = permissions.get(role, [])

    if intent not in allowed_intents:
        return False, f"Access denied. Your role '{role}' is not allowed to perform '{intent}'."

    return True, "Access granted."


def log_request(
    user_id: str,
    query: str,
    intent: str,
    agent_used: str,
    tool_used: str,
    status: str,
    response_time: float,
):
    """
    Stores graph execution logs in SQLite.
    """
    save_log(
        user_id=user_id,
        query=query,
        intent=intent,
        agent_used=agent_used,
        tool_used=tool_used,
        status=status,
        response_time=response_time,
    )