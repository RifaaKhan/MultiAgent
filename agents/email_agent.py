import os
import requests
from dotenv import load_dotenv

from llm_config import get_flash_model
from prompt_loader import load_prompt
from agents.agent_utils import extract_json

load_dotenv()


def generate_email_content(request_type: str, user: dict, details: str):
    llm = get_flash_model()
    prompt_template = load_prompt("email_agent_prompt.txt")

    prompt = f"""
{prompt_template}

Request Type:
{request_type}

User:
{user}

Details:
{details}
"""

    response = llm.invoke(prompt)
    parsed = extract_json(response.content)

    return {
        "subject": parsed.get("subject", f"{request_type} Notification"),
        "body": parsed.get("body", details),
    }


def send_email_via_power_automate(to_email: str, subject: str, body: str):
    flow_url = os.getenv("POWER_AUTOMATE_EMAIL_URL")

    if not flow_url:
        return "Power Automate email URL is not configured."

    payload = {
        "to": to_email,
        "subject": subject,
        "body": body,
    }

    try:
        response = requests.post(flow_url, json=payload, timeout=15)

        if response.status_code in [200, 201, 202]:
            return "Email sent successfully through Power Automate."

        return f"Power Automate email failed. Status code: {response.status_code}"

    except Exception as error:
        return f"Email sending failed: {error}"


def generate_and_send_email(request_type: str, user: dict, details: str):
    email_content = generate_email_content(
        request_type=request_type,
        user=user,
        details=details,
    )

    email_status = send_email_via_power_automate(
        to_email=user["email"],
        subject=email_content["subject"],
        body=email_content["body"],
    )

    return {
        "subject": email_content["subject"],
        "body": email_content["body"],
        "email_status": email_status,
    }