from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json
from tools import add_employee


def run_admin_agent(user: dict, message: str):
    if user["role"] != "Admin":
        return "Access denied. Only Admin can add employees."

    llm = get_flash_model()
    prompt_template = load_prompt("admin_agent_prompt.txt")

    prompt = f"""
{prompt_template}

Admin User:
{user}

Message:
{message}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    action = parsed.get("action", "unknown")

    if parsed.get("user_id") == user["user_id"]:
        parsed["user_id"] = ""

    if parsed.get("name") == user["name"]:
        parsed["name"] = ""

    if action == "add_employee":
        required = ["user_id", "name", "role", "department", "email"]
        missing = [field for field in required if not parsed.get(field)]

        if missing:
            friendly = {
                "user_id": "User ID",
                "name": "Name",
                "role": "Role",
                "department": "Department",
                "email": "Email",
            }
            missing_readable = [friendly[m] for m in missing]
            return f"Please provide the following details: {', '.join(missing_readable)}."

        return add_employee(
            user_id=parsed["user_id"],
            name=parsed["name"],
            role=parsed["role"],
            department=parsed["department"],
            email=parsed["email"],
        )

    return "Please provide employee details to add a new employee."