import asyncio
from aiohttp import ClientSession
import uuid, time
import logging
from concurrent.futures._base import CancelledError
from easyrpc.register import create_proxy_from_config
from easyrpc.auth import encode

class EasyRpcProxy:
    def __init__(
        self,
        origin_host: str,
        origin_port: int,
        origin_path: str,
        server_secret: str,
        encryption_enabled = False,
        loop=None
    ):
        self.origin_host = origin_host
        self.origin_port = origin_port
        self.origin_path = origin_path
        self.server_secret = server_secret
        self.encryption_enabled = encryption_enabled

        self.sessions = {}
        self.session_id = str(uuid.uuid1())
        self.client_connections = {}
        self.setup_logger()

        self.receive_locked = False

        self.proxy_funcs = {}
        self.loop = asyncio.get_running_loop() if not loop else loop

        self.run_cron(
            self.get_origin_registered_functions,
            60
        )
    @classmethod
    async def create(cls,         
        origin_host: str,
        origin_port: int,
        origin_path: str,
        server_secret: str,
        encryption_enabled = False,
        loop=None
    ):
        proxy = cls(
            origin_host, 
            origin_port, 
            origin_path,
            server_secret,
            encryption_enabled,
            loop=loop
        )
        await proxy.get_origin_registered_functions()
        return proxy

    def run_cron(self, action, interval):
        async def cron():
            self.log.warning(f"creating cron or {action.__name__} - interval {interval}")
            while True:
                try:
                    await asyncio.sleep(interval)
                    await action()
                except Exception as e:
                    if not isinstance(e, CancelledError):
                        self.log.exception(f"exceptoin running cron job for {action.__name__}")
                    break
            self.run_cron(action, interval)
            
        self.loop.create_task(cron())

    def setup_logger(self, logger=None, level=None):
        if logger == None:
            level = logging.DEBUG if level == 'DEBUG' else logging.ERROR
            logging.basicConfig(
                level=level,
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                datefmt='%m-%d %H:%M'
            )
            self.log = logging.getLogger(f'wsRpc-proxy')
            self.log.propogate = False
            self.log.setLevel(level)

    async def get_origin_registered_functions(self):
        # issue action 'get_registered_functions'
        config = await self.make_proxy_request({'action': 'get_registered_functions'})
        for func in config['funcs']:
            for f_name, cfg in func.items():
                if not f_name in self.proxy_funcs:
                    self.proxy_funcs[f_name] = create_proxy_from_config(
                        cfg,
                        get_proxy(self, f_name)
                    )

    async def cleanup_proxy_session(self):
        try:
            await self.client_connections[self.session_id].asend('finished')
        except StopAsyncIteration:
            pass
        del self.client_connections[self.session_id]

    async def get_endpoint_sessions(self, endpoint):
        """
        pulls endpoint session if exists else creates & returns
        """
        loop = asyncio.get_running_loop()
        async def session():
            async with ClientSession(loop=loop) as client:
                #trace(f"started session for endpoint {endpoint}")
                while True:
                    status = yield client
                    if status == 'finished':
                        #trace(f"finished session for endpoint {endpoint}")
                        break
        if not endpoint in self.sessions:
            self.sessions[endpoint] = [{'session': session(), 'loop': loop}]
            return await self.sessions[endpoint][0]['session'].asend(None)
        for client in self.sessions[endpoint]:
            if loop == client['loop']:
                return await client['session'].asend(endpoint)

        #log.warning("session existed but not for this event loop, creating")
        client = session()
        self.sessions[endpoint].append({'session': client, 'loop': loop})
        return await client.asend(None)

    async def get_proxy_ws_session(self):
        """
        pulls endpoint session if exists else creates & returns
        """
        async def ws_client():
            encoded_id = encode(self.server_secret, **{'id': self.session_id})
            session = await self.get_endpoint_sessions(self.session_id)
            url = f"http://{self.origin_host}:{self.origin_port}{self.origin_path}"
            async with session.ws_connect(
                url #timeout=600, heartbeat=120.0
                ) as ws:
                async def keep_alive():
                    last_ping = time.time()
                    try:
                        while True:
                            if time.time() - last_ping > 10:
                                result = await ws.send_str('ping')
                                self.log.warning(f"ping send: {result}")
                                while self.receive_locked:
                                    await asyncio.sleep(0.01)
                                try:
                                    self.receive_locked = True
                                    result = await ws.receive()
                                    self.receive_locked = False
                                except Exception as e:
                                    self.receive_locked = False
                                    raise e
                                self.log.warning(f" keep alive receive {result}")
                                last_ping = time.time()
                            await asyncio.sleep(3)
                    except Exception as e:
                        if not isinstance(e, CancelledError):
                            self.log.exception(f"keep alive exiting")
                await ws.send_json({'auth': encoded_id})
                loop = asyncio.get_event_loop()
                loop.create_task(keep_alive())
                while True:
                    status = yield ws
                    if status == 'finished':
                        self.log.debug(f"########### status is {status} #######")
                        break
            return
        if self.session_id and not self.session_id in self.client_connections:
            self.client_connections[self.session_id] = ws_client()
            return await self.client_connections[self.session_id].asend(None)
        return await self.client_connections[self.session_id].asend(None)

    async def make_proxy_request(self, request: dict):
        for _ in range(2):
            try:
                ws = await self.get_proxy_ws_session()
                if self.encryption_enabled:
                    request = encode(self.server_secret, data=request)
                await ws.send_json(request) 

                while self.receive_locked:
                    await asyncio.sleep(0.01)
                self.receive_locked = True
                try:
                    result = await ws.receive_json()
                    if 'error' in result:
                        raise Exception(result['error'])
                except Exception as e:
                    self.receive_locked = False
                    raise e
                self.receive_locked = False
                return result
            except Exception as e:
                last_exception = e
                self.log.exception(f"error during make_proxy_request")
                await self.cleanup_proxy_session()
                continue
        raise last_exception
def get_proxy(ws_proxy: EasyRpcProxy, func_name: str):
    async def proxy(**kwargs):
        return await ws_proxy.make_proxy_request(
            {
                'action': func_name,
                'kwargs': kwargs
            }
        )
    return proxy