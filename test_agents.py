from tools import get_user
from agents.hr_agent import run_hr_agent
from agents.it_agent import run_it_agent
from agents.rag_agent import run_rag_agent
from agents.email_agent import generate_email_content
from agents.approval_agent import run_approval_agent


def main():
    employee = get_user("EMP001")
    manager = get_user("MGR001")
    it_user = get_user("IT001")

    print("\nHR Agent Test:")
    print(run_hr_agent(employee, "Check my leave balance"))

    print("\nIT Agent Test:")
    print(run_it_agent(employee, "Raise a high priority ticket for Outlook not opening"))

    print("\nIT Technician Access Test:")
    print(run_it_agent(it_user, "Show all IT tickets"))

    print("\nRAG Agent Test:")
    print(run_rag_agent("What is the notice period policy?"))

    print("\nEmail Agent Test:")
    print(generate_email_content(
        request_type="Leave Request",
        user=employee,
        details="Employee requested casual leave from 2026-05-02 to 2026-05-03."
    ))

    print("\nApproval Agent Test:")
    print(run_approval_agent(manager, "Approve leave request LEAVE-1"))


if __name__ == "__main__":
    main()