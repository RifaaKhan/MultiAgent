import time
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END

from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import get_user, save_memory
from agents.hr_agent import run_hr_agent
from agents.it_agent import run_it_agent
from agents.rag_agent import run_rag_agent
from agents.email_agent import generate_email_content
from agents.admin_agent import run_admin_agent
from agents.approval_agent import run_approval_agent
from agents.records_agent import run_records_agent
from middleware import (
    rate_limit_check,
    retry_llm_call,
    validate_role_before_tool,
    log_request,
)


class CopilotState(TypedDict, total=False):
    user_id: str
    user: dict
    message: str
    intent: str
    intent_reason: str
    allowed: bool
    agent_used: str
    tool_used: str
    response: Any
    final_response: str
    error: Optional[str]
    start_time: float


def get_latest_user_message(message: str) -> str:
    if "Latest user message:" in message:
        return message.split("Latest user message:")[-1].strip()
    return message.strip()


def load_user_node(state: CopilotState) -> CopilotState:
    user = get_user(state["user_id"])

    if not user:
        return {
            **state,
            "error": "Invalid user. Please select a valid user.",
            "final_response": "Invalid user. Please select a valid user.",
        }

    return {
        **state,
        "user": user,
        "start_time": time.time(),
    }


def rate_limit_node(state: CopilotState) -> CopilotState:
    allowed, message = rate_limit_check(state["user_id"])

    if not allowed:
        return {
            **state,
            "allowed": False,
            "error": message,
            "final_response": message,
        }

    return {
        **state,
        "allowed": True,
    }


def admin_agent_node(state: CopilotState) -> CopilotState:
    response = run_admin_agent(state["user"], state["message"])

    return {
        **state,
        "agent_used": "Admin Agent",
        "tool_used": state["intent"],
        "response": response,
    }


def records_agent_node(state: CopilotState) -> CopilotState:
    response = run_records_agent(state["user"], state["message"])

    return {
        **state,
        "agent_used": "Records Agent",
        "tool_used": state["intent"],
        "response": response,
    }


def detect_intent_node(state: CopilotState) -> CopilotState:
    latest_message = get_latest_user_message(state["message"])
    latest_lower = latest_message.lower().strip()

    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    if latest_lower in greetings:
        return {
            **state,
            "intent": "capabilities",
            "intent_reason": "Greeting detected",
        }

    not_well_phrases = ["not well", "sick", "ill", "fever", "medical appointment", "doctor"]
    if any(phrase in latest_lower for phrase in not_well_phrases):
        return {
            **state,
            "intent": "apply_leave",
            "intent_reason": "Health-related leave need detected",
        }

    if "approve" in latest_lower or "reject" in latest_lower:
        return {
            **state,
            "intent": "approval",
            "intent_reason": "Detected approval action from latest user message",
        }

    llm = get_flash_model()
    router_prompt = load_prompt("router_prompt.txt")

    prompt = f"""
{router_prompt}

User:
{state["user"]}

Message:
{state["message"]}
"""

    try:
        def call_llm():
            return llm.invoke(prompt)

        response = retry_llm_call(call_llm)
        parsed = extract_json(response.content)

        return {
            **state,
            "intent": parsed.get("intent", "unknown"),
            "intent_reason": parsed.get("reason", "Detected by Router Agent"),
        }

    except Exception as error:
        return {
            **state,
            "intent": "unknown",
            "intent_reason": str(error),
            "error": "LLM unavailable. Please try again later.",
            "final_response": "I am currently facing high load. Please try again in a few seconds.",
        }


def role_validation_node(state: CopilotState) -> CopilotState:
    allowed, message = validate_role_before_tool(
        user=state["user"],
        intent=state["intent"],
    )

    if not allowed:
        return {
            **state,
            "allowed": False,
            "error": message,
            "final_response": message,
        }

    return {
        **state,
        "allowed": True,
    }


def capabilities_node(state: CopilotState) -> CopilotState:
    role = state["user"]["role"]

    common = """
Hi, how can I help you?

I can help with:
- HR policy questions
- Leave balance and leave status
- Applying and cancelling leave
- IT ticket creation and tracking
- Asset requests
- Viewing records based on your role
"""

    role_extra = {
        "Employee": "- You can view only your own leave requests and IT tickets.",
        "Manager": "- You can view employees, leave requests, pending approvals, and approve leaves/assets.",
        "HR Team": "- You can view employees, leave records, and approve leave requests.",
        "IT Team": "- You can view tickets/assets and update ticket status.",
        "Admin": "- You can add/view employees and view overall records.",
    }

    response = common + "\n" + role_extra.get(role, "")

    return {
        **state,
        "agent_used": "Capabilities Agent",
        "tool_used": "capabilities",
        "response": response.strip(),
    }


def hr_agent_node(state: CopilotState) -> CopilotState:
    response = run_hr_agent(state["user"], state["message"])

    return {
        **state,
        "agent_used": "HR Agent",
        "tool_used": state["intent"],
        "response": response,
    }


def it_agent_node(state: CopilotState) -> CopilotState:
    response = run_it_agent(state["user"], state["message"])

    return {
        **state,
        "agent_used": "IT Agent",
        "tool_used": state["intent"],
        "response": response,
    }


def rag_agent_node(state: CopilotState) -> CopilotState:
    response = run_rag_agent(state["message"])

    return {
        **state,
        "agent_used": "RAG Agent",
        "tool_used": "ChromaDB + Gemini/Groq",
        "response": response,
    }


def approval_agent_node(state: CopilotState) -> CopilotState:
    response = run_approval_agent(state["user"], state["message"])

    return {
        **state,
        "agent_used": "Approval Agent",
        "tool_used": "approve_request",
        "response": response,
    }


def email_agent_node(state: CopilotState) -> CopilotState:
    response = generate_email_content(
        request_type="General Notification",
        user=state["user"],
        details=state["message"],
    )

    return {
        **state,
        "agent_used": "Email Agent",
        "tool_used": "generate_email_content",
        "response": response,
    }


def analytics_node(state: CopilotState) -> CopilotState:
    return {
        **state,
        "agent_used": "Analytics Agent",
        "tool_used": "analytics",
        "response": "Analytics can show ticket count, leave requests, asset requests, and system activity.",
    }


def unknown_node(state: CopilotState) -> CopilotState:
    return {
        **state,
        "agent_used": "Fallback Agent",
        "tool_used": "none",
        "response": (
            "Sorry, I am not built to handle that request. "
            "I can help with HR policies, leave requests, IT tickets, asset requests, approvals, and role-based records."
        ),
    }


def final_response_node(state: CopilotState) -> CopilotState:
    response = state.get("response", state.get("final_response", ""))

    if isinstance(response, list):
        response_text = "\n".join(str(item) for item in response)
    elif isinstance(response, dict):
        response_text = "\n".join(f"{key}: {value}" for key, value in response.items())
    else:
        response_text = str(response)

    save_memory(
        user_id=state["user_id"],
        user_message=state["message"],
        bot_response=response_text,
    )

    return {
        **state,
        "final_response": response_text,
    }


def log_node(state: CopilotState) -> CopilotState:
    end_time = time.time()
    start_time = state.get("start_time", end_time)
    response_time = round(end_time - start_time, 3)

    status = "Failed" if state.get("error") else "Success"

    log_request(
        user_id=state["user_id"],
        query=state["message"],
        intent=state.get("intent", "unknown"),
        agent_used=state.get("agent_used", "None"),
        tool_used=state.get("tool_used", "None"),
        status=status,
        response_time=response_time,
    )

    return state


def should_continue_after_load_user(state: CopilotState) -> str:
    if state.get("error"):
        return "log"
    return "rate_limit"


def should_continue_after_rate_limit(state: CopilotState) -> str:
    if state.get("error"):
        return "log"
    return "detect_intent"


def should_continue_after_role_validation(state: CopilotState) -> str:
    if state.get("error"):
        return "log"
    return "route"


def route_by_intent(state: CopilotState) -> str:
    intent = state.get("intent", "unknown")

    if intent in ["apply_leave", "leave_balance", "leave_status", "cancel_leave"]:
        return "hr_agent"

    if intent in ["create_ticket", "ticket_status", "asset_request", "update_ticket"]:
        return "it_agent"

    if intent == "policy_question":
        return "rag_agent"

    if intent in ["approval", "show_pending_leaves"]:
        return "approval_agent"

    if intent in ["add_employee", "delete_employee"]:
        return "admin_agent"

    if intent in ["show_employees", "view_records"]:
        return "records_agent"

    if intent == "email":
        return "email_agent"

    if intent == "analytics":
        return "analytics"

    if intent == "capabilities":
        return "capabilities"

    return "unknown"

def build_graph():
    graph = StateGraph(CopilotState)

    graph.add_node("load_user", load_user_node)
    graph.add_node("rate_limit", rate_limit_node)
    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("role_validation", role_validation_node)

    graph.add_node("hr_agent", hr_agent_node)
    graph.add_node("it_agent", it_agent_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("approval_agent", approval_agent_node)
    graph.add_node("email_agent", email_agent_node)
    graph.add_node("analytics", analytics_node)
    graph.add_node("unknown", unknown_node)
    graph.add_node("capabilities", capabilities_node)
    graph.add_node("admin_agent", admin_agent_node)
    graph.add_node("records_agent", records_agent_node)

    graph.add_node("final_response", final_response_node)
    graph.add_node("log", log_node)

    graph.set_entry_point("load_user")

    graph.add_conditional_edges(
        "load_user",
        should_continue_after_load_user,
        {
            "rate_limit": "rate_limit",
            "log": "log",
        },
    )

    graph.add_conditional_edges(
        "rate_limit",
        should_continue_after_rate_limit,
        {
            "detect_intent": "detect_intent",
            "log": "log",
        },
    )

    graph.add_edge("detect_intent", "role_validation")

    graph.add_conditional_edges(
        "role_validation",
        should_continue_after_role_validation,
        {
            "route": "route_decision",
            "log": "log",
        },
    )

    graph.add_node("route_decision", lambda state: state)

    graph.add_conditional_edges(
        "route_decision",
        route_by_intent,
        {
            "hr_agent": "hr_agent",
            "it_agent": "it_agent",
            "rag_agent": "rag_agent",
            "approval_agent": "approval_agent",
            "email_agent": "email_agent",
            "analytics": "analytics",
            "unknown": "unknown",
            "capabilities": "capabilities",
            "admin_agent": "admin_agent",
            "records_agent": "records_agent",
        },
    )

    graph.add_edge("hr_agent", "final_response")
    graph.add_edge("it_agent", "final_response")
    graph.add_edge("rag_agent", "final_response")
    graph.add_edge("approval_agent", "final_response")
    graph.add_edge("email_agent", "final_response")
    graph.add_edge("analytics", "final_response")
    graph.add_edge("unknown", "final_response")
    graph.add_edge("capabilities", "final_response")
    graph.add_edge("admin_agent", "final_response")
    graph.add_edge("records_agent", "final_response")

    graph.add_edge("final_response", "log")
    graph.add_edge("log", END)

    return graph.compile()


copilot_graph = build_graph()


def run_copilot(user_id: str, message: str) -> str:
    result = copilot_graph.invoke({
        "user_id": user_id,
        "message": message,
    })

    return result.get("final_response", "No response generated.")


def run_tests():
    print("\nGraph Test 1: Policy Question")
    print(run_copilot("EMP001", "What is the notice period policy?"))

    print("\nGraph Test 2: Leave Balance")
    print(run_copilot("EMP001", "Check my leave balance"))

    print("\nGraph Test 3: IT Ticket")
    print(run_copilot("EMP001", "Raise a high priority ticket for printer not working"))

    print("\nGraph Test 4: IT Team View")
    print(run_copilot("IT001", "Show all IT tickets"))

    print("\nGraph Test 5: Access Denied")
    print(run_copilot("EMP001", "Approve leave request LEAVE-1"))

    print("\nGraph Test 6: LLM Fallback Intent")
    print(run_copilot("EMP001", "My office email keeps crashing whenever I open it"))


if __name__ == "__main__":
    run_tests()