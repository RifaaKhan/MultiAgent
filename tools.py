import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/enterprise.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, name, role, department, email FROM users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    return {
        "user_id": user[0],
        "name": user[1],
        "role": user[2],
        "department": user[3],
        "email": user[4],
    }


def get_leave_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT casual_leave, sick_leave, earned_leave
        FROM leave_balance
        WHERE user_id = ?
    """, (user_id,))

    balance = cursor.fetchone()
    conn.close()

    if not balance:
        return "Leave balance not found for this user."

    return {
        "casual_leave": balance[0],
        "sick_leave": balance[1],
        "earned_leave": balance[2],
    }


def apply_leave(user_id, leave_type, start_date, end_date, reason):
    user = get_user(user_id)

    if not user:
        return "Invalid user. Leave request cannot be created."

    if leave_type not in ["casual", "sick", "earned"]:
        return "Invalid leave type. Use casual, sick, or earned."

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    if end < start:
        return "End date cannot be before start date."

    total_days = (end - start).days + 1

    balance = get_leave_balance(user_id)

    if isinstance(balance, str):
        return balance

    leave_column = f"{leave_type}_leave"
    available_days = balance[leave_column]

    if total_days > available_days:
        return f"Leave rejected. You requested {total_days} days, but only {available_days} {leave_type} leave days are available."

    conn = get_connection()
    cursor = conn.cursor()

    # Check overlapping leave requests
    cursor.execute("""
        SELECT request_id
        FROM leave_requests
        WHERE user_id = ?
        AND status != 'Cancelled'
        AND NOT (end_date < ? OR start_date > ?)
    """, (user_id, start_date, end_date))

    overlap = cursor.fetchone()

    if overlap:
        conn.close()
        return "Leave request already exists for overlapping dates."

    cursor.execute("""
        INSERT INTO leave_requests
        (user_id, leave_type, start_date, end_date, reason, status, approver_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        leave_type,
        start_date,
        end_date,
        reason,
        "Pending Manager Approval",
        "MGR001"
    ))

    request_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return f"Leave request created successfully. Request ID: LEAVE-{request_id}. Status: Pending Manager Approval."


def check_leave_status(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT request_id, leave_type, start_date, end_date, status
        FROM leave_requests
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No leave requests found."

    result = []
    for row in rows:
        result.append({
            "request_id": f"LEAVE-{row[0]}",
            "leave_type": row[1],
            "start_date": row[2],
            "end_date": row[3],
            "status": row[4],
        })

    return result


def cancel_leave(user_id, request_id):
    clean_id = str(request_id).replace("LEAVE-", "")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT request_id, status
        FROM leave_requests
        WHERE request_id = ? AND user_id = ?
    """, (clean_id, user_id))

    leave = cursor.fetchone()

    if not leave:
        conn.close()
        return "Leave request not found or you do not have access to cancel it."

    if leave[1] == "Approved":
        conn.close()
        return "Approved leave cannot be cancelled from chatbot. Please contact HR."

    cursor.execute("""
        UPDATE leave_requests
        SET status = 'Cancelled'
        WHERE request_id = ? AND user_id = ?
    """, (clean_id, user_id))

    conn.commit()
    conn.close()

    return f"Leave request LEAVE-{clean_id} cancelled successfully."


def create_ticket(user_id, issue_type, description, priority="Medium"):
    user = get_user(user_id)

    if not user:
        return "Invalid user. Ticket cannot be created."

    conn = get_connection()
    cursor = conn.cursor()

    # Check duplicate open ticket
    cursor.execute("""
        SELECT ticket_id
        FROM it_tickets
        WHERE user_id = ?
        AND issue_type = ?
        AND status IN ('Open', 'In Progress')
    """, (user_id, issue_type))

    duplicate = cursor.fetchone()

    if duplicate:
        conn.close()
        return f"You already have an open ticket for {issue_type}. Ticket ID: IT-{duplicate[0]}."

    cursor.execute("""
        INSERT INTO it_tickets
        (user_id, issue_type, description, priority, status, assigned_engineer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        issue_type,
        description,
        priority,
        "Open",
        "IT Team"
    ))

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return f"IT ticket created successfully. Ticket ID: IT-{ticket_id}. Status: Open. Assigned to IT Team."


def get_ticket_status(user_id, role):
    conn = get_connection()
    cursor = conn.cursor()

    if role in ["IT Team", "Admin"]:
        cursor.execute("""
            SELECT ticket_id, user_id, issue_type, priority, status, assigned_engineer
            FROM it_tickets
            ORDER BY created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT ticket_id, user_id, issue_type, priority, status, assigned_engineer
            FROM it_tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No IT tickets found."

    result = []
    for row in rows:
        result.append({
            "ticket_id": f"IT-{row[0]}",
            "user_id": row[1],
            "issue_type": row[2],
            "priority": row[3],
            "status": row[4],
            "assigned_engineer": row[5],
        })

    return result


def create_asset_request(user_id, asset_type, reason):
    user = get_user(user_id)

    if not user:
        return "Invalid user. Asset request cannot be created."

    conn = get_connection()
    cursor = conn.cursor()

    # Check duplicate active asset request
    cursor.execute("""
        SELECT request_id, status
        FROM asset_requests
        WHERE user_id = ?
        AND asset_type = ?
        AND status IN ('Pending Manager Approval', 'Pending IT Approval', 'Approved')
    """, (user_id, asset_type))

    duplicate = cursor.fetchone()

    if duplicate:
        conn.close()
        return f"You already have an active request for {asset_type}. Request ID: ASSET-{duplicate[0]}. Status: {duplicate[1]}."

    cursor.execute("""
        INSERT INTO asset_requests
        (user_id, asset_type, reason, status)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        asset_type,
        reason,
        "Pending Manager Approval"
    ))

    request_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return f"Asset request created successfully. Request ID: ASSET-{request_id}. Status: Pending Manager Approval."


def approve_request(approver_id, request_type, request_id, decision):
    approver = get_user(approver_id)

    if not approver:
        return "Invalid approver."

    if request_type == "leave" and approver["role"] not in ["Manager", "HR Team"]:
        return "Access denied. Only Manager or HR Team can approve leave requests."

    if request_type == "asset" and approver["role"] not in ["Manager"]:
        return "Access denied. Only Manager can approve asset requests."

    if decision not in ["Approved", "Rejected"]:
        return "Invalid decision. Use Approved or Rejected."

    clean_id = str(request_id).replace("LEAVE-", "").replace("ASSET-", "")

    conn = get_connection()
    cursor = conn.cursor()

    if request_type == "leave":
        cursor.execute("""
            UPDATE leave_requests
            SET status = ?
            WHERE request_id = ?
        """, (decision, clean_id))

    elif request_type == "asset":
        cursor.execute("""
            UPDATE asset_requests
            SET status = ?
            WHERE request_id = ?
        """, (decision, clean_id))

    else:
        conn.close()
        return "Invalid request type. Use leave or asset."

    if cursor.rowcount == 0:
        conn.close()
        return "Request not found."

    conn.commit()
    conn.close()

    return f"{request_type.capitalize()} request {request_id} has been {decision}."


def save_memory(user_id, user_message, bot_response):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_memory (user_id, user_message, bot_response)
        VALUES (?, ?, ?)
    """, (user_id, user_message, bot_response))

    conn.commit()
    conn.close()


def save_log(user_id, query, intent, agent_used, tool_used, status, response_time=0.0):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs
        (user_id, query, intent, agent_used, tool_used, status, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        query,
        intent,
        agent_used,
        tool_used,
        status,
        response_time
    ))

    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, name, role, department, email
        FROM users
        ORDER BY name
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "user_id": row[0],
            "name": row[1],
            "role": row[2],
            "department": row[3],
            "email": row[4],
        }
        for row in rows
    ]


def get_pending_leave_requests():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lr.request_id, lr.user_id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.reason, lr.status
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.status = 'Pending Manager Approval'
        ORDER BY lr.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "request_id": f"LEAVE-{row[0]}",
            "user_id": row[1],
            "name": row[2],
            "leave_type": row[3],
            "start_date": row[4],
            "end_date": row[5],
            "reason": row[6],
            "status": row[7],
        }
        for row in rows
    ]


def get_all_asset_requests():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ar.request_id, ar.user_id, u.name, ar.asset_type, ar.reason, ar.status
        FROM asset_requests ar
        JOIN users u ON ar.user_id = u.user_id
        ORDER BY ar.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "request_id": f"ASSET-{row[0]}",
            "user_id": row[1],
            "name": row[2],
            "asset_type": row[3],
            "reason": row[4],
            "status": row[5],
        }
        for row in rows
    ]


def update_ticket_status(ticket_id, status):
    clean_id = str(ticket_id).replace("IT-", "")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE it_tickets
        SET status = ?
        WHERE ticket_id = ?
    """, (status, clean_id))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        return "Ticket not found."

    return f"Ticket IT-{clean_id} updated to {status}."


def get_analytics_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leave_requests")
    total_leaves = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leave_requests WHERE status LIKE 'Pending%'")
    pending_leaves = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM it_tickets")
    total_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM it_tickets WHERE status IN ('Open', 'In Progress')")
    open_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM asset_requests")
    total_assets = cursor.fetchone()[0]

    conn.close()

    return {
        "total_leaves": total_leaves,
        "pending_leaves": pending_leaves,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "total_assets": total_assets,
    }

def get_used_leave_days(user_id, leave_type):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT start_date, end_date
        FROM leave_requests
        WHERE user_id = ?
        AND leave_type = ?
        AND status = 'Approved'
    """, (user_id, leave_type))

    rows = cursor.fetchall()
    conn.close()

    used_days = 0

    for start_date, end_date in rows:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        used_days += (end - start).days + 1

    return used_days


def get_leave_balance_report(user_id, leave_type=None):
    balance = get_leave_balance(user_id)

    if isinstance(balance, str):
        return balance

    leave_types = {
        "casual": "casual_leave",
        "sick": "sick_leave",
        "earned": "earned_leave",
    }

    if leave_type:
        leave_type = leave_type.lower()

        if leave_type not in leave_types:
            return "Invalid leave type. Please ask for casual, sick, or earned leave."

        total = balance[leave_types[leave_type]]
        used = get_used_leave_days(user_id, leave_type)
        remaining = total - used

        return (
            f"You have {total} {leave_type} leaves in total. "
            f"You have consumed {used} {leave_type} leaves. "
            f"Remaining {leave_type} leaves: {remaining}."
        )

    reports = []

    for leave_name, column_name in leave_types.items():
        total = balance[column_name]
        used = get_used_leave_days(user_id, leave_name)
        remaining = total - used

        reports.append(
            f"{leave_name.capitalize()} Leave → Total: {total}, Used: {used}, Remaining: {remaining}"
        )

    return "\n".join(reports)


def get_all_leave_requests():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lr.request_id, lr.user_id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.reason, lr.status
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.user_id
        ORDER BY lr.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "request_id": f"LEAVE-{row[0]}",
            "user_id": row[1],
            "name": row[2],
            "leave_type": row[3],
            "start_date": row[4],
            "end_date": row[5],
            "reason": row[6],
            "status": row[7],
        }
        for row in rows
    ]

def add_employee(user_id, name, role, department, email):
    allowed_roles = ["Employee", "Manager", "HR Team", "IT Team", "Admin"]

    if role not in allowed_roles:
        return f"Invalid role. Allowed roles: {', '.join(allowed_roles)}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return f"User {user_id} already exists."

    cursor.execute("""
        INSERT INTO users (user_id, name, role, department, email)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, name, role, department, email))

    cursor.execute("""
        INSERT INTO leave_balance (user_id, casual_leave, sick_leave, earned_leave)
        VALUES (?, 12, 10, 15)
    """, (user_id,))

    conn.commit()
    conn.close()

    return f"Employee {name} ({user_id}) added successfully with role {role}."

def format_pending_leave_requests():
    pending_leaves = get_pending_leave_requests()

    if not pending_leaves:
        return "No pending leave requests found."

    lines = ["Pending Leave Requests:\n"]

    for leave in pending_leaves:
        lines.append(
            f"Request ID: {leave['request_id']}\n"
            f"Employee: {leave['name']} ({leave['user_id']})\n"
            f"Leave Type: {leave['leave_type']}\n"
            f"Dates: {leave['start_date']} to {leave['end_date']}\n"
            f"Reason: {leave['reason'] or 'Not specified'}\n"
            f"Status: {leave['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)

def cancel_asset_request(user_id, request_id):
    clean_id = str(request_id).replace("ASSET-", "")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT request_id, status
        FROM asset_requests
        WHERE request_id = ? AND user_id = ?
    """, (clean_id, user_id))

    asset = cursor.fetchone()

    if not asset:
        conn.close()
        return "Asset request not found or you do not have access to cancel it."

    if asset[1] == "Approved":
        conn.close()
        return "Approved asset request cannot be cancelled from chatbot. Please contact IT."

    cursor.execute("""
        UPDATE asset_requests
        SET status = 'Cancelled'
        WHERE request_id = ? AND user_id = ?
    """, (clean_id, user_id))

    conn.commit()
    conn.close()

    return f"Asset request ASSET-{clean_id} cancelled successfully."

def get_asset_requests_by_status(status_filter=None):
    assets = get_all_asset_requests()

    if not status_filter:
        return assets

    status_filter = status_filter.lower()

    return [
        asset for asset in assets
        if asset["status"].lower() == status_filter
    ]


def format_asset_requests(assets, title="Asset Requests"):
    if not assets:
        return f"No {title.lower()} found."

    lines = [f"{title}:\n"]

    for asset in assets:
        lines.append(
            f"Request ID: {asset['request_id']}\n"
            f"Employee: {asset.get('name', 'Unknown')} ({asset['user_id']})\n"
            f"Asset: {asset['asset_type']}\n"
            f"Reason: {asset.get('reason') or 'Not specified'}\n"
            f"Status: {asset['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)


def format_open_it_tickets():
    tickets = get_ticket_status(user_id="", role="IT Team")

    if not isinstance(tickets, list):
        return tickets

    open_tickets = [
        ticket for ticket in tickets
        if ticket["status"] in ["Open", "In Progress"]
    ]

    if not open_tickets:
        return "No open IT tickets found."

    lines = ["Open IT Tickets:\n"]

    for ticket in open_tickets:
        lines.append(
            f"Ticket ID: {ticket['ticket_id']}\n"
            f"User: {ticket['user_id']}\n"
            f"Issue: {ticket['issue_type']}\n"
            f"Priority: {ticket['priority']}\n"
            f"Status: {ticket['status']}\n"
            f"{'-' * 35}"
        )

    return "\n".join(lines)

def get_leave_request_owner(request_id):
    clean_id = str(request_id).replace("LEAVE-", "")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.user_id, u.name, u.role, u.department, u.email,
               lr.request_id, lr.leave_type, lr.start_date, lr.end_date, lr.status
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.request_id = ?
    """, (clean_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "name": row[1],
        "role": row[2],
        "department": row[3],
        "email": row[4],
        "request_id": f"LEAVE-{row[5]}",
        "leave_type": row[6],
        "start_date": row[7],
        "end_date": row[8],
        "status": row[9],
    }

def get_asset_requests_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT request_id, user_id, asset_type, reason, status
        FROM asset_requests
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No asset requests found."

    return [
        {
            "request_id": f"ASSET-{row[0]}",
            "user_id": row[1],
            "asset_type": row[2],
            "reason": row[3],
            "status": row[4],
        }
        for row in rows
    ]

def delete_employee(user_id):
    user = get_user(user_id)

    if not user:
        return f"User {user_id} not found."

    if user_id == "ADMIN001":
        return "Default admin user cannot be deleted."

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM leave_requests WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM leave_balance WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM it_tickets WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM asset_requests WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM chat_memory WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM logs WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    return f"Employee {user['name']} ({user_id}) and related records deleted successfully."


def run_tests():
    print("\nTesting tools.py...\n")

    print("1. Checking user:")
    print(get_user("EMP001"))

    print("\n2. Checking leave balance:")
    print(get_leave_balance("EMP001"))

    print("\n3. Applying leave:")
    print(apply_leave(
        user_id="EMP001",
        leave_type="casual",
        start_date="2026-05-02",
        end_date="2026-05-03",
        reason="Personal work"
    ))

    print("\n4. Checking leave status:")
    print(check_leave_status("EMP001"))

    print("\n5. Creating IT ticket:")
    print(create_ticket(
        user_id="EMP001",
        issue_type="VPN",
        description="VPN is not connecting",
        priority="High"
    ))

    print("\n6. Checking ticket status as Employee:")
    print(get_ticket_status("EMP001", "Employee"))

    print("\n7. Creating asset request:")
    print(create_asset_request(
        user_id="EMP001",
        asset_type="Laptop",
        reason="Need laptop for project work"
    ))

    print("\n8. Approving leave as Manager:")
    print(approve_request(
        approver_id="MGR001",
        request_type="leave",
        request_id="LEAVE-1",
        decision="Approved"
    ))

    print("\nTool testing completed.")


if __name__ == "__main__":
    run_tests()