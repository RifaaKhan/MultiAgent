from fastmcp import FastMCP

from tools import (
    apply_leave,
    get_leave_balance,
    create_ticket,
    get_ticket_status,
)

mcp = FastMCP("Enterprise Copilot MCP Server")


@mcp.tool
def mcp_get_leave_balance(user_id: str) -> dict | str:
    """
    Get leave balance for a user from SQLite database.
    """
    return get_leave_balance(user_id)


@mcp.tool
def mcp_apply_leave(
    user_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str,
) -> str:
    """
    Apply leave for a user and store the request in SQLite database.

    Date format must be YYYY-MM-DD.
    Leave type must be casual, sick, or earned.
    """
    return apply_leave(
        user_id=user_id,
        leave_type=leave_type.lower(),
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )


@mcp.tool
def mcp_create_ticket(
    user_id: str,
    issue_type: str,
    description: str,
    priority: str = "Medium",
) -> str:
    """
    Create an IT support ticket for a user in SQLite database.
    """
    return create_ticket(
        user_id=user_id,
        issue_type=issue_type,
        description=description,
        priority=priority,
    )


@mcp.tool
def mcp_get_ticket_status(user_id: str, role: str) -> list | str:
    """
    Get IT ticket status.

    Employees can see only their own tickets.
    IT Team and Admin can see all tickets.
    """
    return get_ticket_status(user_id=user_id, role=role)


if __name__ == "__main__":
    mcp.run()