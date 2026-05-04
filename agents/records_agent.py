from tools import (
    get_all_users,
    get_all_leave_requests,
    check_leave_status,
    get_ticket_status,
    get_all_asset_requests,
    get_asset_requests_for_user,
    format_asset_requests,
)


def get_latest_user_message(message: str) -> str:
    if "Latest user message:" in message:
        return message.split("Latest user message:")[-1].strip()
    return message.strip()


def format_users(users):
    if not users:
        return "No employees found."

    lines = ["Employees:\n"]

    for user in users:
        lines.append(
            f"User ID: {user['user_id']}\n"
            f"Name: {user['name']}\n"
            f"Role: {user['role']}\n"
            f"Department: {user['department']}\n"
            f"Email: {user['email']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def format_leaves(leaves, title="Leave Requests"):
    if isinstance(leaves, str):
        return leaves

    if not leaves:
        return f"No {title.lower()} found."

    lines = [f"{title}:\n"]

    for leave in leaves:
        employee = ""
        if "name" in leave and "user_id" in leave:
            employee = f"Employee: {leave['name']} ({leave['user_id']})\n"

        lines.append(
            f"Request ID: {leave['request_id']}\n"
            f"{employee}"
            f"Leave Type: {leave['leave_type']}\n"
            f"Dates: {leave['start_date']} to {leave['end_date']}\n"
            f"Status: {leave['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def format_tickets(tickets, title="IT Tickets"):
    if isinstance(tickets, str):
        return tickets

    if not tickets:
        return f"No {title.lower()} found."

    lines = [f"{title}:\n"]

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


def format_my_assets(assets):
    if isinstance(assets, str):
        return assets

    if not assets:
        return "No asset requests found."

    lines = ["My Asset Requests:\n"]

    for asset in assets:
        lines.append(
            f"Request ID: {asset['request_id']}\n"
            f"Asset: {asset['asset_type']}\n"
            f"Reason: {asset.get('reason') or 'Not specified'}\n"
            f"Status: {asset['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def run_records_agent(user: dict, message: str):
    role = user["role"]
    user_id = user["user_id"]

    latest_message = get_latest_user_message(message)
    text = latest_message.lower()

    if "employee" in text or "employees" in text:
        if role in ["Admin", "Manager", "HR Team"]:
            return format_users(get_all_users())
        return "Access denied. You are not allowed to view employee records."

    if "ticket" in text or "tickets" in text:
        if "my" in text or role not in ["Admin", "IT Team"]:
            return format_tickets(get_ticket_status(user_id, role), "My IT Tickets")

        return format_tickets(get_ticket_status(user_id, role), "All IT Tickets")

    if "asset" in text or "assets" in text:
        if "my" in text:
            return format_my_assets(get_asset_requests_for_user(user_id))

        if role in ["Admin", "Manager", "HR Team", "IT Team"]:
            return format_asset_requests(get_all_asset_requests(), "All Asset Requests")

        return "Access denied. Employees cannot view all asset requests."

    if "leave" in text or "leaves" in text:
        if "my" in text or role == "Employee":
            return format_leaves(check_leave_status(user_id), "My Leave Requests")

        if role in ["Admin", "Manager", "HR Team"]:
            return format_leaves(get_all_leave_requests(), "All Leave Requests")

        return "Access denied. You can view only your own leave requests."

    if "record" in text or "request" in text:
        if "my" in text or role == "Employee":
            my_leaves = format_leaves(check_leave_status(user_id), "My Leave Requests")
            my_tickets = format_tickets(get_ticket_status(user_id, role), "My IT Tickets")
            my_assets = format_my_assets(get_asset_requests_for_user(user_id))
            return f"{my_leaves}\n\n{my_tickets}\n\n{my_assets}"

        leaves = ""
        tickets = ""
        assets = ""

        if role in ["Admin", "Manager", "HR Team"]:
            leaves = format_leaves(get_all_leave_requests(), "All Leave Requests")

        if role in ["Admin", "IT Team"]:
            tickets = format_tickets(get_ticket_status(user_id, role), "All IT Tickets")

        if role in ["Admin", "Manager", "HR Team", "IT Team"]:
            assets = format_asset_requests(get_all_asset_requests(), "All Asset Requests")

        return "\n\n".join(part for part in [leaves, tickets, assets] if part)

    return "Please specify what records you want to view: employees, leaves, tickets, or assets."