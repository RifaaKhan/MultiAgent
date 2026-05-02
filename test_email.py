from agents.email_agent import send_email_via_power_automate

result = send_email_via_power_automate(
    to_email="Azkiya.Khan@novigosolutions.com",
    subject="Test Email From Enterprise Copilot",
    body="This is a test email sent from Python to Power Automate."
)

print(result)