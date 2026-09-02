import asyncio
from aiohttp import web
from app.config import settings
async def health(request):return web.Response(text='AMAN OK')
async def run_health_server():
    app=web.Application();app.router.add_get('/',health);runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'0.0.0.0',settings.WEB_PORT);await site.start();return runner
