# client.py
import asyncio, traceback
from easyrpc.proxy import EasyRpcProxy

class EasyRpcProxyLogger(EasyRpcProxy):
    async def info(self, message):
        await self['info'](message)
    async def warning(self, message):
        await self['warning'](message)
    async def error(self, message):
        await self['error'](message)
    async def debugger(self, message):
        await self['debug'](message)
    async def exception(self, message):
        stack_trace = traceback.format_exc()
        await self['exception'](message, stack_trace)



async def main():
    logger = await EasyRpcProxyLogger.create(
        '0.0.0.0', 
        8220, 
        '/ws/logger', 
        server_secret='abcd1234',
        namespace='logger'
    )

    await logger.warning(f"Logger starting from {logger.session_id}")

    try:
        d = {}
        d['a'] == 'invalid'
    except Exception:
        await logger.exception(f"error applying value to {d}")




asyncio.run(main())