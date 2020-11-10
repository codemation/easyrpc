import uuid, time, json
import logging
import asyncio
from concurrent.futures._base import CancelledError

from aiohttp import ClientSession
from easyrpc.register import (
    create_proxy_from_config, 
    Coroutine, 
    Generator, 
    AsyncGenerator, 
    async_generator_asend
)
from easyrpc.auth import encode
from easyrpc.origin import Origin
from easyrpc.generator import RpcGenerator

class EasyRpcProxy:
    def __init__(
        self,
        origin_host: str = None,
        origin_port: int = None,
        origin_path: str = None,
        origin_id: str = None,
        session_id: str = None,
        server_secret: str = None,
        namespace: str = 'DEFAULT',
        proxy_type: str = 'PROXY', # PROXY | SERVER_PROXY | SERVER
        encryption_enabled: bool = False,
        server = None, #EasyRpcServer
        loop=None,
        logger: logging.Logger = None,
        debug: bool = False
    ):
        self.kind = 'PROXY'
        self.loop = asyncio.get_running_loop() if not loop else loop

        self.origin_host = origin_host
        self.origin_port = origin_port
        self.origin_path = origin_path
        self.origin_id = origin_id
        self.server_secret = server_secret
        self.namespace = namespace
        self.proxy_type = proxy_type
        self.encryption_enabled = encryption_enabled

        # reference to local EasyRpcServer 
        self.server = server
        self.origin = Origin(self)
        self.namespaces = {}

        self.sessions = {}
        self.session_id = str(uuid.uuid1()) if not session_id else session_id
        self.client_connections = {}

        self.debug = debug
        if self.server:
            logger = self.server.log
        self.setup_logger(logger=logger, level='DEBUG' if self.debug else 'ERROR')

        self.proxy_funcs = {}

        self.jobs = []
        if proxy_type == 'SERVER':
            self.run_cron(
                self.get_upstream_registered_functions,
                30
            )
        elif proxy_type == 'PROXY':
            self.run_cron(
                self.get_all_registered_functions,
                30
            )
        else:
            self.run_cron(
                self.get_downstream_registered_functions,
                30
            )
        
    def __getitem__(self, func):
        if func in self.proxy_funcs:
            return self.proxy_funcs[func]
        raise IndexError(f"function {func} not found")
    def __del__(self):
        for job in self.jobs.copy():
            try:
                job.cancel()
            except Exception as e:
                self.log.exception(f"error canceling job")

    @classmethod
    async def create(cls,         
        origin_host: str = None,
        origin_port: int = None,
        origin_path: str = None,
        origin_id: str = None,
        session_id: str = None,
        server_secret: str = None,
        namespace: str = 'DEFAULT',
        proxy_type: str = 'PROXY',
        encryption_enabled = False,
        server = None,
        loop=None,
        debug: bool = False,
    ):
        proxy = cls(
            origin_host, 
            origin_port, 
            origin_path,
            origin_id,
            session_id,
            server_secret,
            namespace,
            proxy_type,
            encryption_enabled,
            server=server,
            loop=loop,
            debug=debug
        )
        """
        proxy_type:
            Server - request all upstream registered functions in namespace and register non existing in local namespace instance
            ServerProxy - request all downstream registered functions, register new functions in local namespace instance
        """
        if proxy_type =='SERVER':
            await proxy.get_upstream_registered_functions()
        elif proxy_type == 'PROXY':
            await proxy.get_all_registered_functions()
        else:
            await proxy.get_downstream_registered_functions()
        return proxy

    def run_cron(self, action, interval):
        async def cron():
            self.log.warning(f"creating cron or {action.__name__} - interval {interval}")
            tasks = []
            while True:
                try:
                    tasks = []
                    await asyncio.sleep(interval)
                    tasks.append(self.loop.create_task(action()))
                except Exception as e:
                    if not isinstance(e, CancelledError):
                        self.log.exception(f"exceptoin running cron job for {action.__name__}")
                    break
            for task in tasks:
                try:
                    task.cancel()
                except Exception:
                    pass
            
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
        else:
            self.log = logger
    async def get_namespace_functions(self, upstream=True, all_functions=False, trigger=None):
        config = await self.proxy_request(
            {
                'action': 'get_registered_functions', 
                'args': [self.namespace],
                'kwargs': {
                    'upstream': upstream,
                    'all_functions': all_functions,
                    'trigger': trigger
                    }
            }
        )
        if not config:
            return
        
        namespaces = [self.namespace]
        if self.server and self.namespace in self.server.namespace_groups:
            namespaces = list(self.server.namespace_groups[self.namespace])
        
        for namespace in namespaces:
            self.namespaces[namespace] = {}
            for func in config['funcs']:
                for f_name, cfg in func.items():
                    self.proxy_funcs[f_name] = create_proxy_from_config(
                        cfg,
                        get_proxy(self, f_name)
                    )
                self.origin(self.proxy_funcs[f_name], namespace=namespace)
    async def get_downstream_registered_functions(self):
        return await self.get_namespace_functions(upstream=False)

    async def get_upstream_registered_functions(self):
        return await self.get_namespace_functions(trigger=self.session_id)
    async def get_all_registered_functions(self):
        return await self.get_namespace_functions(all_functions=True)

    async def get_origin_registered_functions(self):
        # issue action 'get_registered_functions' on origin
        
        config = await self.proxy_request({'action': 'get_registered_functions', 'args': [self.namespace]})

        proxy_funcs = set()
        for func in config['funcs']:
            for f_name, cfg in func.items():
                proxy_funcs.add(f_name)
                if not f_name in self.proxy_funcs:
                    self.proxy_funcs[f_name] = create_proxy_from_config(
                        cfg,
                        get_proxy(self, f_name)
                    )
        
        if self.server:
            for func_name, func in self.proxy_funcs.items():
                if not func_name in self.server.namespaces[self.namespace]:
                    self.server.origin(func, namespace=self.namespace)
    
    async def cleanup_proxy_session(self):
        if not self.session_id in self.client_connections:
            return
        try:
            await self.client_connections[self.session_id].asend('finished')
        except StopAsyncIteration:
            pass
        if self.session_id in self.client_connections:
            del self.client_connections[self.session_id]
        if self.session_id in self.sessions:
            session = self.sessions.pop(self.session_id)
            try:
                await session[0]['session'].asend('finished')
            except StopAsyncIteration:
                pass
        self.proxy_funcs = {}
        self.namespaces = {}
    
    async def get_endpoint_sessions(self):
        loop = asyncio.get_running_loop()
        async def session():
            async with ClientSession(loop=loop) as client:
                while True:
                    status = yield client
                    if status == 'finished':
                        self.log.debug(f"ClientSession cleaning up")
                        break
        if not self.session_id in self.sessions:
            self.sessions[self.session_id] = [{'session': session(), 'loop': loop}]
            return await self.sessions[self.session_id][0]['session'].asend(None)
        for client in self.sessions[self.session_id]:
            if loop == client['loop']:
                return await client['session'].asend(self.session_id)

        client = session()
        self.sessions[self.session_id].append({'session': client, 'loop': loop})
        return await client.asend(None)

    async def get_proxy_ws_session(self):
        """
        pulls endpoint session if exists else creates & returns
        """
        async def ws_client():
            self.client_send_queue = asyncio.Queue()
            self.requests = {}
            setup = {
                'type': self.proxy_type,
                'id': self.session_id, 
                'namespace': self.namespace
                }
            setup = encode(self.server_secret, **setup)
            session = await self.get_endpoint_sessions()
            url = f"http://{self.origin_host}:{self.origin_port}{self.origin_path}"

            async with session.ws_connect(
                url #timeout=600, heartbeat=120.0
                ) as ws:
                async def ws_sender():
                    try:
                        empty = True
                        while True:
                            if empty:
                                request = await self.client_send_queue.get()
                                empty = False
                            else:
                                try:
                                    request = self.client_send_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    empty = True
                                    continue
                            await ws.send_json(request)
                    except Exception as e:
                        if not isinstance(e, CancelledError):
                            self.log.exception(f"error with ws_sender")
                    await self.cleanup_proxy_session()
                async def ws_receiver():
                    try:
                        while True:
                            message = await ws.receive()
                            self.log.debug(f"received message: {message}")
                            if message.data == None:
                                break
                            if 'error' in message.data and not 'ws_action' in message.data:
                                break
                            if 'ws_action' in message.data:
                                message = json.loads(message.data)
                                if message['ws_action']['type'] == 'response':
                                    queue = self.requests.get(message['ws_action']['request_id'])
                                    if queue:
                                        await queue.put(message['ws_action']['response'])

                                if message['ws_action']['type'] == 'request':
                                    request = message['ws_action']['request']
                                    request_id = message['ws_action']['request_id']
                                    response_expected = message['ws_action']['response_expected']

                                    if not self.server:
                                        await self.client_send_queue.put({
                                            'ws_action': {
                                                'type': 'response',
                                                'response': {"error": "proxy has no associated EasyRpcServer"},
                                                'request_id': request_id
                                            }
                                        })
                                        continue

                                    if self.encryption_enabled:
                                        request = decode(request, self.server_secret)['data']

                                    if not 'action' in request:
                                        await self.client_send_queue.put({
                                            'ws_action': {
                                                'type': 'response',
                                                'response': {"error": "missing expected input: 'action' "},
                                                'request_id': request_id
                                            }
                                        })
                                        continue
                                    action = request['action']
                                    self.log.debug(f"###### proxy_type {self.proxy_type} action: {action} #####")

                                    if action == 'get_registered_functions':
                                        # get_registered_functions
                                        executed_action = self.server.get_registered_functions(
                                            namespace=self.namespace, 
                                            **request['kwargs']
                                        )
                                        self.log.debug(f"ORIGIN action: get_registered_functions")
                                    elif action == 'GENERATOR_NEXT':
                                        generator_id = request['generator_id']
                                        if not generator_id in self.server.server_generators:
                                            self.log.debug(f"no generator exists with request_id {generator_id}")
                                        executed_action = self.server.server_generators[generator_id].asend(None)     

                                    else:
                                        if not action in self.server[self.namespace]:
                                            await self.client_send_queue.put({
                                                'ws_action': {
                                                    'type': 'response',
                                                    'response': {"error": f"no action {action} registered for origin within {self.server[namespace]}"},
                                                    'request_id': request_id
                                                }
                                            })
                                            continue

                                        executed_action = self.server.run(
                                            self.namespace,
                                            action,
                                            request['args'] if 'args' in request else [],
                                            request['kwargs'] if 'kwargs' in request else {},
                                        )
                                        self.log.debug(f"ORIGIN action: {action}")
                                    
                                    if type(executed_action) in {Coroutine, async_generator_asend}:
                                        try:
                                            response = await executed_action
                                        except StopAsyncIteration as e:
                                            response = 'GENERATOR_END'
                                    elif type(executed_action) in {Generator, AsyncGenerator}:
                                        self.server.server_generators[request_id] = RpcGenerator(
                                            executed_action
                                        )
                                        response = {'GENERATOR_START': request_id}

                                    else:
                                        response = executed_action
                                    
                                    if response_expected:

                                        await self.client_send_queue.put({
                                            'ws_action': {
                                                'type': 'response',
                                                'response': response,
                                                'request_id': request_id
                                            }
                                        })
                                    
                                
                    except Exception as e:
                        if not isinstance(e, CancelledError):
                            self.log.exception(f"error with ws_receiver")
                    await self.cleanup_proxy_session()

                async def keep_alive():
                    last_ping = time.time()
                    try:
                        while True:
                            if time.time() - last_ping > 10:
                                await self.client_send_queue.put({'ping': 'ping'})
                                last_ping = time.time()
                            await asyncio.sleep(5)
                    except Exception as e:
                        if not isinstance(e, CancelledError):
                            self.log.exception(f"keep alive exiting")
                
                loop = asyncio.get_event_loop()

                # enable send/receive receive workers
               
                # send inital auth token
                try:
                    await ws.send_json({'setup': setup})
                    setup_response = await ws.receive()
                    self.log.debug(f"setup response: {setup_response}")
                except Exception as e:
                    self.log.exception(f"error during setup")
                    return

                if 'error' in setup_response.data:
                    self.log.debug(f"auth_response: {setup_response.data}")
                    return
                setup_response = json.loads(setup_response.data)
                self.origin_id = setup_response['server_id']

                # session jobs    
                self.jobs.append(loop.create_task(ws_sender()))
                self.jobs.append(loop.create_task(ws_receiver()))
                self.jobs.append(loop.create_task(keep_alive()))

                while True:
                    status = yield ws
                    if status == 'finished':
                        self.log.debug(f"########### status is {status} #######")
                        break

            self.proxy_funcs = {}
            self.namespaces = {}
            return

        if self.session_id and not self.session_id in self.client_connections:
            self.client_connections[self.session_id] = ws_client()
            return await self.client_connections[self.session_id].asend(None)
        try:
            return await self.client_connections[self.session_id].asend(None)
        except StopAsyncIteration:
            await self.cleanup_proxy_session()
    async def proxy_update(self, update):
        """
        sends ws_action type 'update' to relative server
        """
        if self.proxy_type == 'SERVER_PROXY':
            if self.encryption_enabled:
                request = encode(self.server.server_secret, data=request)

            await self.server.server_send_queue[self.origin_id].put(update)
        else:
            await self.client_send_queue.put(update)

    async def proxy_generator(self, request_id, generator_id):
        async def generator():
            ws_action = {
                'ws_action': {
                    'type': 'request',
                    'response_expected': True,
                    'request': {'action': 'GENERATOR_NEXT', 'generator_id': generator_id},
                    'request_id': request_id
                }
            }    
            while True:
                await self.client_send_queue.put(ws_action)
                result = await self.requests[request_id].get()
                if result == 'GENERATOR_END':
                    break
                status = yield result
                if 'status' == 'finished':
                    break
            del self.requests[request_id]

            if not self.proxy_type == 'PROXY':
                del self.server.server_generators[generator_id]
        proxy_gen = generator()
        if not self.proxy_type == 'PROXY':
            self.server.server_generators[generator_id] = proxy_gen
        else:
            return proxy_gen

    async def proxy_request(self, request, response_expected=True):
        """
        invokes ws.send_json(request) 
        response_expected = True Default)
            waits for response to request_id
        """
        #self.log.debug(f"proxy_request: {request}")
        if self.proxy_type == 'SERVER_PROXY':
            if self.encryption_enabled:
                request = encode(self.server.server_secret, data=request)
            result = await self.server.server_request(
                self.origin_id,
                request
            )
            if response_expected:
                return result
            return
        try:
            #self.log.debug(f"proxy_request: getting ws_session")
            ws = await self.get_proxy_ws_session()
            #self.log.debug(f"proxy_request: ws_session {ws}")
            if self.encryption_enabled:
                request = encode(self.server_secret, data=request)
            request_id = str(uuid.uuid1())
            ws_action = {
                'ws_action': {
                    'type': 'request',
                    'response_expected': response_expected,
                    'request': request,
                    'request_id': request_id
                }
            }
            if response_expected:
                self.requests[request_id] = asyncio.Queue(1)

            await self.client_send_queue.put(ws_action)

            if response_expected:
                #self.log.debug(f"proxy_request: waiting for result")
                result =  await self.requests[request_id].get()
                if 'GENERATOR_START' in result:
                    generator_id = result['GENERATOR_START']
                    proxy_generator = await self.proxy_generator(request_id, generator_id)
                    if self.proxy_type == 'PROXY':
                        return proxy_generator
                    return result
                #self.log.debug(f"proxy_request: result {result}")
                del self.requests[request_id]
                return result
        except Exception as e:
            self.log.exception("error with proxy_request")
            raise e


def get_proxy(ws_proxy: EasyRpcProxy, func_name: str):
    async def proxy(*args, **kwargs):
        return await ws_proxy.proxy_request(
            {
                'action': func_name,
                'args': list(args),
                'kwargs': kwargs
            }
        )
    return proxy