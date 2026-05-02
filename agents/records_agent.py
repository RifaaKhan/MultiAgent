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

    lines = ["Employees:"]
    for user in users:
        lines.append(
            f"{user['user_id']} | {user['name']} | Role: {user['role']} | "
            f"Department: {user['department']} | Email: {user['email']}"
        )
    return "\n".join(lines)


def format_leaves(leaves, title="Leave Requests"):
    if isinstance(leaves, str):
        return leaves

    if not leaves:
        return f"No {title.lower()} found."

    lines = [f"{title}:"]
    for leave in leaves:
        employee = ""
        if "name" in leave and "user_id" in leave:
            employee = f"Employee: {leave['name']} ({leave['user_id']}) | "

        lines.append(
            f"{leave['request_id']} | "
            f"{employee}"
            f"Type: {leave['leave_type']} | "
            f"Dates: {leave['start_date']} to {leave['end_date']} | "
            f"Status: {leave['status']}"
        )
    return "\n".join(lines)


def format_tickets(tickets, title="IT Tickets"):
    if isinstance(tickets, str):
        return tickets

    if not tickets:
        return f"No {title.lower()} found."

    lines = [f"{title}:"]
    for ticket in tickets:
        lines.append(
            f"{ticket['ticket_id']} | User: {ticket['user_id']} | "
            f"Issue: {ticket['issue_type']} | Priority: {ticket['priority']} | "
            f"Status: {ticket['status']} | Assigned: {ticket['assigned_engineer']}"
        )
    return "\n".join(lines)


def format_my_assets(assets):
    if isinstance(assets, str):
        return assets

    if not assets:
        return "No asset requests found."

    lines = ["My Asset Requests:"]

    for asset in assets:
        lines.append(
            f"{asset['request_id']} | "
            f"Asset: {asset['asset_type']} | "
            f"Reason: {asset['reason']} | "
            f"Status: {asset['status']}"
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