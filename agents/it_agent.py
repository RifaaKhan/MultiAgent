from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import (
    create_ticket,
    get_ticket_status,
    create_asset_request,
    cancel_asset_request,
    update_ticket_status,
    get_all_asset_requests,
    get_asset_requests_by_status,
    format_asset_requests,
    format_open_it_tickets,
)


def format_tickets(tickets):
    if not isinstance(tickets, list):
        return tickets

    if not tickets:
        return "No IT tickets found."

    lines = ["IT Tickets:\n"]

    for ticket in tickets:
        lines.append(
            f"Ticket ID: {ticket['ticket_id']}\n"
            f"User: {ticket['user_id']}\n"
            f"Issue: {ticket['issue_type']}\n"
            f"Priority: {ticket['priority']}\n"
            f"Status: {ticket['status']}\n"
            f"Assigned Engineer: {ticket['assigned_engineer']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def run_it_agent(user: dict, message: str):
    message_lower = message.lower()
    role = user["role"]

    if role == "IT Team":
        if "pending approval" in message_lower or "pending approvals" in message_lower or "open requests" in message_lower:
            open_assets = get_asset_requests_by_status("Pending Manager Approval")
            asset_text = format_asset_requests(open_assets, "Open Asset Requests")
            ticket_text = format_open_it_tickets()
            return f"{asset_text}\n\n{ticket_text}"

        if "open asset" in message_lower or "open assets" in message_lower:
            open_assets = get_asset_requests_by_status("Pending Manager Approval")
            return format_asset_requests(open_assets, "Open Asset Requests")

        if "all asset" in message_lower or "all assets" in message_lower:
            return format_asset_requests(get_all_asset_requests(), "All Asset Requests")

        if "open ticket" in message_lower or "open tickets" in message_lower:
            return format_open_it_tickets()

    if role == "Admin":
        if "all asset" in message_lower or "all assets" in message_lower:
            return format_asset_requests(get_all_asset_requests(), "All Asset Requests")

        if "all ticket" in message_lower or "all tickets" in message_lower:
            return format_tickets(get_ticket_status(user["user_id"], role))

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
        restricted_words = ["other employees", "all employees", "emp002", "another employee"]

        if role == "Employee" and any(word in message_lower for word in restricted_words):
            return "Access denied. Employees can view only their own IT tickets."

        return format_tickets(get_ticket_status(user["user_id"], role))

    if action == "create_asset_request":
        if not parsed.get("asset_type"):
            return "Please provide the asset type you need."

        return create_asset_request(
            user_id=user["user_id"],
            asset_type=parsed["asset_type"],
            reason=parsed.get("reason", message),
        )

    if action == "cancel_asset_request":
        request_id = parsed.get("request_id")

        if not request_id:
            return "Please provide the asset request ID to cancel. Example: Cancel ASSET-1."

        return cancel_asset_request(
            user_id=user["user_id"],
            request_id=request_id,
        )

    if action == "update_ticket_status":
        if role not in ["IT Team", "Admin"]:
            return "Access denied. Only IT Team or Admin can update ticket status."

        ticket_id = parsed.get("ticket_id")
        status = parsed.get("status")

        if not ticket_id or not status:
            return "Please provide ticket ID and status. Example: Close ticket IT-1."

        return update_ticket_status(ticket_id, status)

    return "I could not understand the IT request clearly."