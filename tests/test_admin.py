from app.admin.permissions import role_allows
from app.models import AdminRole

def test_rbac_sensitive_matrix():
    assert role_allows(AdminRole.SUPER_ADMIN,"payments.approve")
    assert role_allows(AdminRole.FINANCE,"payments.approve") and not role_allows(AdminRole.FINANCE,"support.reply")
    assert role_allows(AdminRole.SUPPORT,"support.reply") and not role_allows(AdminRole.SUPPORT,"payments.approve")
    assert role_allows(AdminRole.OPERATIONS,"phones.edit") and not role_allows(AdminRole.OPERATIONS,"settings.write")
    assert role_allows(AdminRole.VIEWER,"customers.read") and not role_allows(AdminRole.VIEWER,"customers.block")

def test_a_is_not_permission(): assert not role_allows(AdminRole.VIEWER,"admin_mode")
