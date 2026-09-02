from ..models import AdminRole

PERMISSIONS = {
    AdminRole.SUPER_ADMIN: {"*"},
    AdminRole.FINANCE: {"read", "payments.read", "payments.approve", "payments.reject", "subscriptions.read", "subscriptions.renew", "subscriptions.extend", "reports.read"},
    AdminRole.SUPPORT: {"read", "customers.read", "phones.read", "support.read", "support.reply", "support.close", "support.reopen", "support.assign"},
    AdminRole.OPERATIONS: {"read", "customers.read", "customers.edit", "customers.block", "phones.read", "phones.edit", "phones.suspend", "subscriptions.read", "subscriptions.renew", "subscriptions.extend", "followups.read", "followups.edit", "payments.read", "reports.read", "faq.read", "faq.write", "notifications.read", "notifications.send", "settings.read"},
    AdminRole.VIEWER: {"read", "customers.read", "phones.read", "subscriptions.read", "payments.read", "support.read", "reports.read", "faq.read", "notifications.read", "audit.read"},
}

def role_allows(role: AdminRole, permission: str) -> bool:
    allowed = PERMISSIONS.get(role, set())
    return "*" in allowed or permission in allowed
