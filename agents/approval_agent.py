from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from agents.email_agent import generate_and_send_email
from tools import (
    approve_request,
    format_pending_leave_requests,
    get_asset_requests_by_status,
    format_asset_requests,
    get_leave_request_owner,
)


def get_latest_user_message(message: str) -> str:
    if "Latest user message:" in message:
        return message.split("Latest user message:")[-1].strip()
    return message.strip()


def normalize_request_id(request_id: str, request_type: str) -> str:
    request_id = str(request_id).strip().upper()

    if request_type == "leave":
        if request_id.isdigit():
            return f"LEAVE-{request_id}"
        if not request_id.startswith("LEAVE-"):
            return f"LEAVE-{request_id}"

    if request_type == "asset":
        if request_id.isdigit():
            return f"ASSET-{request_id}"
        if not request_id.startswith("ASSET-"):
            return f"ASSET-{request_id}"

    return request_id


def format_manager_pending_approvals():
    pending_assets = get_asset_requests_by_status("Pending Manager Approval")
    leave_text = format_pending_leave_requests()
    asset_text = format_asset_requests(pending_assets, "Pending Asset Requests")
    return f"{leave_text}\n\n{asset_text}"


def run_approval_agent(user: dict, message: str):
    latest_message = get_latest_user_message(message)
    latest_lower = latest_message.lower()
    role = user["role"]

    if "pending" in latest_lower or "approval" in latest_lower:
        if role == "Manager":
            return format_manager_pending_approvals()

        if role == "HR Team":
            return format_pending_leave_requests()

        return "Access denied. Your role cannot view approval requests."

    if latest_lower.strip() in ["approve/reject", "approve", "reject"]:
        return "Please provide the request ID. Example: Approve LEAVE-1 or Approve ASSET-2."

    if any(word in latest_lower for word in ["approve", "reject"]):
        llm = get_flash_model()
        prompt_template = load_prompt("approval_agent_prompt.txt")

        prompt = f"""
{prompt_template}

Approver User:
{user}

Latest User Message:
{latest_message}
"""

        response = llm.invoke(prompt)
        parsed = extract_json(response.content)

        request_type = parsed.get("request_type")
        request_id = parsed.get("request_id")
        decision = parsed.get("decision")

        if not request_type or not request_id or not decision:
            return "Please provide request type, request ID, and decision. Example: Approve LEAVE-1."

        if role == "HR Team" and request_type == "asset":
            return "Access denied. HR Team can approve leave requests only."

        request_id = normalize_request_id(request_id, request_type)

        approval_result = approve_request(
            approver_id=user["user_id"],
            request_type=request_type,
            request_id=request_id,
            decision=decision,
        )

        if request_type == "leave" and "has been" in approval_result:
            employee = get_leave_request_owner(request_id)

            if employee:
                email_result = generate_and_send_email(
                    request_type="Leave Approval Confirmation",
                    user=employee,
                    details=approval_result,
                )

                return f"{approval_result}\n\nEmail Status: {email_result['email_status']}"

        return approval_result

    return "Please ask me to show pending approvals or approve/reject a specific request."