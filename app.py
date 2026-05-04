import streamlit as st
import pandas as pd

from graph import run_copilot
from tools import (
    get_all_users,
    get_user,
    check_leave_status,
    get_ticket_status,
    get_pending_leave_requests,
    get_all_leave_requests,
    get_all_asset_requests,
    approve_request,
    update_ticket_status,
    get_analytics_summary,
    add_employee,
)

st.set_page_config(
    page_title="Enterprise AI Copilot",
    page_icon="🤖",
    layout="wide",
)


def format_user_label(user):
    return f"{user['name']} ({user['role']}) - {user['user_id']}"


def get_user_chat_key(user_id):
    return f"messages_{user_id}"


def show_chat(user):
    st.subheader("💬 Enterprise AI Copilot Chat")

    chat_key = get_user_chat_key(user["user_id"])

    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    demo_queries = [
        "What is the notice period policy?",
        "How many sick leaves do I have?",
        "I want to apply sick leave on 2026-04-29 for one day",
        "Raise a high priority ticket for printer not working",
        "Show all IT tickets",
        "Request laptop for project work",
    ]

    with st.expander("Try demo queries"):
        cols = st.columns(2)
        for index, query in enumerate(demo_queries):
            with cols[index % 2]:
                if st.button(query, key=f"demo_{user['user_id']}_{index}"):
                    st.session_state.selected_demo_query = query

    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.code(message["content"])  
            else:
                st.markdown(message["content"])   

    user_input = st.chat_input("Ask about HR policies, leave, IT tickets, assets, or approvals...")

    if "selected_demo_query" in st.session_state:
        user_input = st.session_state.selected_demo_query
        del st.session_state.selected_demo_query

    if user_input:
        st.session_state[chat_key].append({
            "role": "user",
            "content": user_input,
        })

        with st.chat_message("user"):
            st.write(user_input)

        recent_context = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in st.session_state[chat_key][-6:]
        )

        message_with_context = f"""
Conversation context:
{recent_context}

Latest user message:
{user_input}
"""

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = run_copilot(user["user_id"], message_with_context)
                st.code(response)

        st.session_state[chat_key].append({
            "role": "assistant",
            "content": response,
        })


def show_employee_view(user):
    st.subheader("👤 Employee View")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### My Leave Requests")
        leaves = check_leave_status(user["user_id"])
        if isinstance(leaves, list):
            st.dataframe(pd.DataFrame(leaves), use_container_width=True)
        else:
            st.info(leaves)

    with col2:
        st.write("### My IT Tickets")
        tickets = get_ticket_status(user["user_id"], user["role"])
        if isinstance(tickets, list):
            st.dataframe(pd.DataFrame(tickets), use_container_width=True)
        else:
            st.info(tickets)


def show_manager_view(user):
    st.subheader("✅ Manager Leave Approval View")

    pending_leaves = get_pending_leave_requests()

    if pending_leaves:
        st.dataframe(pd.DataFrame(pending_leaves), use_container_width=True)

        request_ids = [request["request_id"] for request in pending_leaves]
        selected_request = st.selectbox("Select Leave Request", request_ids)
        decision = st.selectbox("Decision", ["Approved", "Rejected"])

        if st.button("Submit Leave Decision"):
            result = approve_request(
                approver_id=user["user_id"],
                request_type="leave",
                request_id=selected_request,
                decision=decision,
            )
            st.success(result)
            st.rerun()
    else:
        st.info("No pending leave requests.")


def show_hr_view(user):
    st.subheader("🧾 HR Team Leave Overview")

    leaves = get_all_leave_requests()

    if leaves:
        st.dataframe(pd.DataFrame(leaves), use_container_width=True)
    else:
        st.info("No leave requests found.")


def show_it_view(user):
    st.subheader("🛠️ IT Technician View")

    tickets = get_ticket_status(user["user_id"], user["role"])

    if isinstance(tickets, list):
        st.write("### All IT Tickets")
        st.dataframe(pd.DataFrame(tickets), use_container_width=True)

        st.write("### Update Ticket Status")

        ticket_ids = [ticket["ticket_id"] for ticket in tickets]

        if ticket_ids:
            selected_ticket = st.selectbox("Select Ticket", ticket_ids)
            selected_status = st.selectbox("New Status", ["Open", "In Progress", "Resolved", "Closed"])

            if st.button("Update Ticket"):
                result = update_ticket_status(selected_ticket, selected_status)
                st.success(result)
                st.rerun()
        else:
            st.info("No tickets available.")
    else:
        st.info(tickets)


def show_admin_view(user):
    st.subheader("🛡️ Admin Overview")

    st.info("Admin can monitor overall system analytics, records, and add new employees.")

    st.write("### Add New Employee")

    with st.form("add_employee_form"):
        new_user_id = st.text_input("User ID", placeholder="EMP002")
        new_name = st.text_input("Name")
        new_role = st.selectbox("Role", ["Employee", "Manager", "HR Team", "IT Team", "Admin"])
        new_department = st.text_input("Department")
        new_email = st.text_input("Email")

        submitted = st.form_submit_button("Add Employee")

        if submitted:
            if not new_user_id or not new_name or not new_department or not new_email:
                st.error("Please fill all employee details.")
            else:
                result = add_employee(
                    user_id=new_user_id,
                    name=new_name,
                    role=new_role,
                    department=new_department,
                    email=new_email,
                )
                st.success(result)
                st.rerun()

    st.divider()

    leaves = get_all_leave_requests()
    tickets = get_ticket_status(user["user_id"], user["role"])
    assets = get_all_asset_requests()

    tab1, tab2, tab3 = st.tabs(["Leaves", "Tickets", "Assets"])

    with tab1:
        if leaves:
            st.dataframe(pd.DataFrame(leaves), use_container_width=True)
        else:
            st.info("No leave records.")

    with tab2:
        if isinstance(tickets, list):
            st.dataframe(pd.DataFrame(tickets), use_container_width=True)
        else:
            st.info(tickets)

    with tab3:
        if assets:
            st.dataframe(pd.DataFrame(assets), use_container_width=True)
        else:
            st.info("No asset requests.")


def show_analytics_panel():
    st.subheader("📊 Analytics")

    analytics = get_analytics_summary()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Leaves", analytics["total_leaves"])
    col2.metric("Pending Leaves", analytics["pending_leaves"])
    col3.metric("Total Tickets", analytics["total_tickets"])
    col4.metric("Open Tickets", analytics["open_tickets"])
    col5.metric("Asset Requests", analytics["total_assets"])


def main():
    st.title("Enterprise AI Copilot")
    st.caption("Chat-based HR + IT assistant using LangGraph, RAG, RBAC and LLMs")

    users = get_all_users()

    if not users:
        st.error("No users found. Please run database.py first.")
        return

    with st.sidebar:
        st.header("User Session")

        selected_label = st.selectbox(
            "Select User",
            [format_user_label(user) for user in users],
        )

        selected_user_id = selected_label.split("-")[-1].strip()
        user = get_user(selected_user_id)

        st.write("Role:")
        st.info(user["role"])

        st.write("Department:")
        st.write(user["department"])

        chat_key = get_user_chat_key(user["user_id"])

        if st.button("Clear Chat"):
            st.session_state[chat_key] = []
            st.rerun()

    # ONLY CHAT — NO DASHBOARD
    show_chat(user)


if __name__ == "__main__":
    main()