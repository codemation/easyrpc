# share logging with a basic client
import aysncio
from easyrpc.proxy import EasyRpcProxyLogger

async def main():

    logger = await EasyRpcProxyLogger.create(
        '0.0.0.0', 
        8220, 
        '/ws/server', 
        server_secret='abcd1234', 
        namespace='logger'
    )
    await logger.warning(f"client - started from {logger.session_id}")

aysncio.run(main())