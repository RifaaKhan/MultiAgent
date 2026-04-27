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

    if approver["role"] not in ["Manager", "HR Team", "IT Team", "Admin"]:
        return "Access denied. You do not have approval permission."

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