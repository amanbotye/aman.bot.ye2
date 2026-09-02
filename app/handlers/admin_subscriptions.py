from .admin import admin_text

async def handle(update, context, session, services):
    """Entry point for the subscriptions administrative area; authorization is enforced by the admin service."""
    return await admin_text(update, context, session, services)
