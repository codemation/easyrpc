import asyncio
import uuid, time, json, os
from typing import Callable, Optional
import logging
from concurrent.futures._base import CancelledError

from fastapi import FastAPI
from fastapi.websockets import WebSocket, WebSocketDisconnect

from easyrpc.auth import encode, decode
from easyrpc.origin import Origin
from easyrpc.register import Coroutine, Generator, AsyncGenerator, async_generator_asend
from easyrpc.proxy import EasyRpcProxy
from easyrpc.generator import RpcGenerator


class ConnectionManager:
    def __init__(self, server):
        self.server = server
        self.log = server.log
        self.active_connections = {}

    async def connect(self, websocket: WebSocket):
        return await websocket.accept()

    def store_connect(self, endpoint_id, websocket: WebSocket):
        self.log.warning(f"created websocket connection with endpoint {endpoint_id}")
        self.active_connections[endpoint_id] = websocket

    def disconnect(self, endpoint_id: str):
        self.log.warning(f"deleted websocket connection with endpoint {endpoint_id}")
        del self.active_connections[endpoint_id]
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await self.active_connections[connection].send_text(message)

class EasyRpcServer:
    def __init__(
        self,
        server: FastAPI,    # Fast API Server
        origin_path: str, # path accessed to start WS connection /ws/my_origin_paths
        server_secret: str, 
        encryption_enabled: bool = False,
        logger: logging.Logger = None,
        debug: bool = False
    ):
        self.kind = 'SERVER'
        self.loop = asyncio.get_running_loop()
        self.server = server
        self.origin_path = origin_path
        self.server_secret = server_secret
        self.encryption_enabled = encryption_enabled
        self.setup_logger(logger=logger, level='DEBUG' if debug else 'ERROR')
        self.connection_manager = ConnectionManager(self)

        self.namespaces = {}
        self.namespace_groups = {}

        self.origin = Origin(self)
        self._setup_ws_server(server)

        # send queues
        self.server_send_queue = {}
        self.server_requests = {}

        # generators
        self.server_generators = {}

        # server proxies
        self.server_proxies = {}

        # clients that connect through this server
        self.reverse_proxies = set()

        self.server_id = str(uuid.uuid1())

    @classmethod
    async def create(
        cls,
        server: FastAPI,    # Fast API Server
        origin_path: str, # path accessed to start WS connection /ws/my_origin_paths
        server_secret: str, 
        encryption_enabled: bool = False,
        logger: logging.Logger = None,
        debug: bool = False
    ):
        return cls(
            server,
            origin_path,
            server_secret,
            encryption_enabled,
            logger,
            debug
        )
    async def create_server_proxy(
        self,
        origin_host: str = None,
        origin_port: int = None,
        origin_path: str = None,
        origin_id: str = None,
        session_id: str = None,
        server_secret: str = None,
        namespace: str = 'DEFAULT',
        proxy_type: str = 'SERVER',
        encryption_enabled = False,
        server = None
    ):
        if not namespace in self.server_proxies:
            if not namespace in self.namespace_groups:
                self.server_proxies[namespace] = {}
        if proxy_type == 'SERVER' and 'parent' in self.server_proxies[namespace]:
            raise Exception(f"only 1 parent connection is allowed per EasyRpcServer")


        new_proxy = await EasyRpcProxy.create(
            origin_host, 
            origin_port,
            origin_path,
            origin_id,
            session_id,
            server_secret,
            namespace,
            proxy_type,
            encryption_enabled,
            server=self
        )
        if proxy_type == 'SERVER':
            self.server_proxies[namespace]['parent'] = new_proxy
        else:
            namespaces = [namespace] if not namespace in self.namespace_groups else list(self.namespace_groups[namespace])
            for n_space in namespaces:
                self.server_proxies[n_space][new_proxy.session_id] = new_proxy
    def create_namespace_group(self, group_name: str, *namespaces):
        """
        group two or more namespaces into a single reference space. Functions are not 
        registered to groups but the member namespaces. Namespaces do not allow for 
        duplicate functions, but namespace groups may contain namespaces with same-name 
        functions. When a function is called from a namespace group the first function 
        with the matching name is used, a duplicate could be used in outage or 
        load-balancing scenarios  
        """
        if group_name in self.namespace_groups:
            raise Exception(f"a namespace_group named {group_name} already exists")
        for namespace in namespaces:
            if not namespace in self.namespaces:
                self.namespaces[namespace] = {}
        self.namespace_groups[group_name] = set(namespaces)
        
    def setup_logger(self, logger=None, level=None):
        if logger == None:
            level = logging.DEBUG if level == 'DEBUG' else logging.WARNING
            logging.basicConfig(
                level=level,
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                datefmt='%m-%d %H:%M'
            )
            self.log = logging.getLogger(f'EasyRpc-server {self.origin_path}')
            self.log.propogate = False
            self.log.setLevel(level)
        else:
            self.log = logger
    def _setup_ws_server(self, server):
        @server.websocket_route(self.origin_path)
        async def origin(websocket: WebSocket):
            # decode auth - determine if valid & add connection
            # add connection to connection manager
            self.log.debug(f"origin ws connection starting {websocket}")
            result = await self.connection_manager.connect(websocket)
            
            setup = await websocket.receive_json()
            
            setup = decode(setup['setup'], self.server_secret, log=self.log)
            self.log.debug(f"setup: {setup}")
            
            if not setup:
                self.log.debug(f"unable to decode auth, server_secret may not match with server")
                await websocket.send_json({
                    "error": f"unable to decode auth, server_secret may not match with server"
                    })
                # sleep to allow error to propogate to client
                return

            decoded_id = setup['id']
            namespace = setup['namespace']
            session_id = setup['id']

            self.connection_manager.store_connect(decoded_id, websocket)

            finished = asyncio.Queue(2)

            # queue of requests to be sent to client
            self.server_send_queue[decoded_id] = asyncio.Queue()

            async def ws_sender():
                try:
                    empty = True
                    while True:
                        if empty:
                            request = await self.server_send_queue[decoded_id].get()
                            empty = False
                        else:
                            try:
                                request = self.server_send_queue[decoded_id].get_nowait()
                            except asyncio.QueueEmpty:
                                empty = True
                                continue
                        self.log.debug(f"ws_sender - request: {request}")
                        await websocket.send_json(request)
                except Exception as e:
                    if not isinstance(e, CancelledError):
                        self.log.exception(f"error with ws_sender")
                await finished.put('finished')

            async def ws_receiver():
                try:
                    while True:
                        message = await websocket.receive()
                        if 'text' in message and 'ping' in message['text']:
                            await self.server_send_queue[decoded_id].put({'pong': 'pong'})
                        
                        if message['type'] == 'websocket.disconnect':
                            raise WebSocketDisconnect

                        message = json.loads(message['text'])
                        self.log.debug(f"received message: {message}")

                        if 'ws_action' in message:  
                            if message['ws_action']['type'] == 'response':
                                queue = self.server_requests.get(message['ws_action']['request_id'])
                                if queue:
                                    await queue.put(message['ws_action']['response'])
                            if message['ws_action']['type'] == 'request':
                                
                                request = message['ws_action']['request']
                                request_id = message['ws_action']['request_id']
                                response_expected = message['ws_action']['response_expected']

                                if self.encryption_enabled:
                                    request = decode(request, self.server_secret,log=self.log)['data']

                                if not 'action' in request:
                                    await self.server_send_queue[decoded_id].put({
                                        'ws_action': {
                                            'type': 'response',
                                            'response': {"error": "missing expected input: 'action' "},
                                            'request_id': request_id
                                        }
                                    })
                                    continue
                                action = request['action']
                                self.log.debug(f"ws_action: {action}")
                                if action == 'get_registered_functions':
                                    # get_registered_functions
                                    executed_action = self.get_registered_functions(
                                        namespace=namespace,
                                        **request['kwargs']
                                    )
                                    self.log.debug(f"ORIGIN action: get_registered_functions")
                                elif action == 'GENERATOR_NEXT':
                                    generator_id = request['generator_id']
                                    if not generator_id in self.server_generators:
                                        self.log.debug(f"no generator exists with request_id {generator_id}")
                                    executed_action = self.server_generators[generator_id].asend(None)

                                else:
                                    if not action in self[namespace]:
                                        self.log.debug(f"ws_receive: {action} not in orgin")
                                        await self.server_send_queue[decoded_id].put({
                                            'ws_action': {
                                                'type': 'response',
                                                'response': {"error": f"no action {action} registered for origin within {self[namespace]}"},
                                                'request_id': request_id
                                            }
                                        })
                                        continue
                                    
                                    
                                    executed_action = self.run(
                                        namespace,
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
                                    self.server_generators[request_id] = RpcGenerator(
                                        executed_action
                                    )
                                    response = {'GENERATOR_START': request_id}
                                else:
                                    response = executed_action
                                
                                if response_expected:
                                    self.log.debug(f"ws_action - response: {response}")
                                    await self.server_send_queue[decoded_id].put({
                                        'ws_action': {
                                            'type': 'response',
                                            'response': response,
                                            'request_id': request_id
                                        }
                                    })


                except Exception as e:
                    if not isinstance(e, CancelledError):
                        self.log.exception(f"error with ws_receiver")
                await finished.put('finished')
            
            loop = asyncio.get_running_loop()
            loop.create_task(
                ws_sender()
            )
            loop.create_task(
                ws_receiver()
            )

            await websocket.send_json({'auth': 'ok', 'server_id': self.server_id})

            self.reverse_proxies.add(session_id)

            if setup['type'] == 'SERVER':
                """
                session was started by a server, need to create proxy to gather 
                server function in namespace, if any
                """
                await self.create_server_proxy(
                    namespace=namespace,
                    proxy_type='SERVER_PROXY',
                    origin_id=decoded_id,
                    session_id=session_id
                )

            try:
                await finished.get()

                # child connection closed
                self.log.warning(f"client websocket connection with id {decoded_id} finished")
                
                # check if child is server or proxy
                if setup['type'] == 'SERVER':
                    
                    if session_id in self.server_proxies[namespace]:
                        del self.server_proxies[namespace][session_id]
                    if session_id in self.reverse_proxies:
                        self.reverse_proxies.remove(session_id)
            except Exception as e:
                if not isinstance(e, CancelledError):
                    self.log.exception(f"error with ws_sender")
            
            self.connection_manager.disconnect(decoded_id)
    async def server_generator(self, client_id, request_id, generator_id):
        async def generator():
            ws_action = {
                'ws_action': {
                    'type': 'request',
                    'response_expected': True,
                    'request': {'action': 'GENERATOR_NEXT', 'generator_id': generator_id},
                    'request_id': request_id
                }
            }
            self.log.debug(f"generator {generator_id} starting")
            while True:
                await self.server_send_queue[client_id].put(ws_action)
                result = await self.server_requests[request_id].get()
                if result == 'GENERATOR_END':
                    break
                status = yield result
                if 'status' == 'finished':
                    break
            self.log.debug(f"generator {generator_id} exiting")
            del self.server_requests[request_id]
            del self.server_generators[generator_id]
        self.server_generators[generator_id] = generator()
    async def server_request(self, client_id, request, response_expected=True):
        """
        invokes websocket.send_json(request) using session with client_id
        response_expected = True (Default)
            waits for response to request_id
        """
        try:
            if self.encryption_enabled:
                request = encode(self.server_secret, data=request, log=self.log)
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
                self.server_requests[request_id] = asyncio.Queue(1)

            await self.server_send_queue[client_id].put(ws_action)


            if response_expected:
                self.log.debug(f"server_request: result {result}")
                result = await self.server_requests[request_id].get()
                if not result:
                    return result
                if 'GENERATOR_START' in result:
                    generator_id = result['GENERATOR_START']
                    await self.server_generator(client_id, request_id, generator_id)
                    return result
                del self.server_requests[request_id]
                return result

        except Exception as e:
            self.log.exception("error during server_request")
    def run(self, namespace, func, args=[], kwargs={}):
        """
        returns function called with given args & kwargs
        if type async, returns coroutine that should be awaited
        """
        if namespace in self.namespaces or namespace in self.namespace_groups:
            if func in self[namespace]:
                return self[namespace][func](
                    *args,
                    **kwargs
                )
        return None
    def get_parent_registered_functions(self, namespace, cfg='config', trigger=None):
        self.log.debug(f"get_parent_registered_functions: ns {namespace} ser_proxies: {self.server_proxies} rev_proxies: {self.reverse_proxies}")
        parent_funcs = []
        if 'parent' in self.server_proxies[namespace] and namespace in self.server_proxies[namespace]['parent'].namespaces:
            for f_name, config in self.server_proxies[namespace]['parent'].namespaces[namespace].items():
                parent_funcs.append({f_name: config[cfg]})
        self.log.debug(f"get_parent_registered_functions: reverse_proxies {self.reverse_proxies}")
        for proxy in self.reverse_proxies:
            if trigger and trigger == proxy:
                continue
            if proxy in self.server_proxies[namespace]:
                self.log.debug(f"get_parent_registered_functions: reverse_proxy {self.server_proxies[namespace][proxy].namespaces[namespace]}")
                for f_name, config in self.server_proxies[namespace][proxy].namespaces[namespace].items():
                    parent_funcs.append({f_name: config[cfg]})

        return parent_funcs
    def get_child_registered_functions(self, namespace, cfg='config'):
        child_funcs = []
        if not namespace in self.server_proxies:
            return child_funcs
        for proxy in self.reverse_proxies:
            if proxy in self.server_proxies[namespace]:
                for f_name, config in self.server_proxies[namespace][proxy].namespaces[namespace].items():
                    child_funcs.append({f_name: config[cfg]})
        return child_funcs

    def get_registered_functions(self, namespace='DEFAULT', upstream=True, cfg='config', trigger=None, all_functions=False):
        if namespace in self.namespace_groups:
            group_funcs = []
            for n_space in self.namespace_groups[namespace]:
                for f in self.namespaces[n_space]:
                    group_funcs.append({f: self.namespaces[n_space][f][cfg]})

                if upstream and n_space in self.server_proxies:
                    group_funcs += self.get_parent_registered_functions(n_space, cfg=cfg, trigger=trigger)

                if all_functions or not upstream:
                    group_funcs += self.get_child_registered_functions(n_space, cfg=cfg)
            return {'funcs': group_funcs}

        # single namespaces    
        self.log.debug(f"get_registered_functions: ns {namespace}, upstream {upstream} cfg {cfg} trigger: {trigger} af {all_functions}")
        local_funcs = [
            {f: self.namespaces[namespace][f][cfg]} for f in self.namespaces[namespace] if namespace in self.namespaces
        ]
        if upstream and namespace in self.server_proxies:
            local_funcs += self.get_parent_registered_functions(namespace, cfg=cfg, trigger=trigger)
        if all_functions or not upstream:
            local_funcs += self.get_child_registered_functions(namespace, cfg=cfg)
        return {
            'funcs': local_funcs
            }
    def get_all_registered_functions(self, namespace):
        all_registered_functions = self.get_registered_functions(
            namespace,
            cfg='method',
            all_functions=True
        )
        registered_functions = {}
        for func in all_registered_functions['funcs']:
            for f_name, method in func.items():
                registered_functions[f_name] = method
        return registered_functions

    def __getitem__(self, namespace):
        if namespace in self.namespace_groups:
            group_functions = {}
            for n_space in self.namespace_groups[namespace]:
                for k, v in self.get_all_registered_functions(n_space).items():
                    if not k in group_functions:
                        group_functions[k] = v
            self.log.debug(f"GET group functions: {group_functions}")
            return group_functions
        if not namespace in self.namespaces:
            raise IndexError(f"no namespace with name {namespace}")
        return self.get_all_registered_functions(namespace)
    