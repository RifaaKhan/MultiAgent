def detect_intent_by_rules(message: str) -> dict:
    text = message.lower()

    # Approval must come BEFORE leave rules
    if any(word in text for word in ["approve", "reject", "approved", "rejected"]):
        return {"intent": "approval", "reason": "Matched approval keywords", "source": "rules"}

    if any(word in text for word in ["notice period", "policy", "casual leave", "sick leave", "work from home", "maternity"]):
        return {"intent": "policy_question", "reason": "Matched policy keywords", "source": "rules"}

    if any(word in text for word in ["leave balance", "available leave", "how many leaves"]):
        return {"intent": "leave_balance", "reason": "Matched leave balance keywords", "source": "rules"}

    if any(word in text for word in ["apply leave", "request leave", "take leave"]):
        return {"intent": "apply_leave", "reason": "Matched apply leave keywords", "source": "rules"}

    if any(word in text for word in ["leave status", "leave history", "my leaves"]):
        return {"intent": "leave_status", "reason": "Matched leave status keywords", "source": "rules"}

    if "cancel leave" in text:
        return {"intent": "cancel_leave", "reason": "Matched cancel leave keywords", "source": "rules"}

    if any(word in text for word in ["ticket status", "show tickets", "my tickets", "all tickets"]):
        return {"intent": "ticket_status", "reason": "Matched ticket status keywords", "source": "rules"}

    if any(word in text for word in ["raise ticket", "create ticket", "not working", "vpn", "outlook", "printer", "network", "software issue"]):
        return {"intent": "create_ticket", "reason": "Matched IT ticket keywords", "source": "rules"}

    if any(word in text for word in ["request laptop", "request monitor", "need laptop", "need monitor", "keyboard", "mouse", "software license", "vpn token"]):
        return {"intent": "asset_request", "reason": "Matched asset request keywords", "source": "rules"}

    if any(word in text for word in ["analytics", "dashboard", "summary", "count"]):
        return {"intent": "analytics", "reason": "Matched analytics keywords", "source": "rules"}

    return {"intent": "unknown", "reason": "No rule matched", "source": "fallback"}