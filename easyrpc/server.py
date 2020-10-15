import asyncio
import uuid, time, json, os
from typing import Callable
import logging
from fastapi import FastAPI
from fastapi.websockets import WebSocket, WebSocketDisconnect

from easyrpc.auth import encode, decode
from easyrpc.orgin import Orgin


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
        orgin_path: str, # path accessed to start WS connection /ws/my_orgin_paths
        server_secret: str, 
        encryption_enabled: bool = False,
        logger: logging.Logger = None,
        debug: bool = False
    ):
        self.server = server
        self.orgin_path = orgin_path
        self.server_secret = server_secret
        self.encryption_enabled = encryption_enabled
        self.setup_logger(logger=logger, level='DEBUG' if debug else 'ERROR')
        self.connection_manager = ConnectionManager(self)
        self.orgin = Orgin(self)
        self.setup_ws_server(server)
    async def create(
        cls,
        server: FastAPI,    # Fast API Server
        orgin_path: str, # path accessed to start WS connection /ws/my_orgin_paths
        server_secret: str, 
        encryption_enabled: bool = False,
        logger: logging.Logger = None,
        debug: bool = False
    ):
        return cls(
            server,
            orgin_path,
            server_secret,
            encryption_enabled,
            logger,
            debug
        )
    def setup_logger(self, logger=None, level=None):
        if logger == None:
            level = logging.DEBUG if level == 'DEBUG' else logging.WARNING
            logging.basicConfig(
                level=level,
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                datefmt='%m-%d %H:%M'
            )
            self.log = logging.getLogger(f'wsRpc-server {self.orgin_path}')
            self.log.propogate = False
            self.log.setLevel(level)
    def setup_ws_server(self, server):
        @server.websocket_route(self.orgin_path)
        async def orgin(websocket: WebSocket):
            # decode auth - determine if valid & add connection
            # add connection to connection manager
            self.log.debug(f"orgin ws connection starting {websocket}")
            result = await self.connection_manager.connect(websocket)

            auth = await websocket.receive_json()

            decoded_id = decode(auth['auth'], self.server_secret)
            
            if not decoded_id:
                self.log.debug(f"unable to decode auth, server_secret may not match with server")
                await websocket.send_json({
                    "error": f"unable to decode auth, server_secret may not match with server"}
                    )
                # sleep to allow error to propogate to client
                await asyncio.sleep(5)
                raise WebSocketDisconnect(f"could not decode auth")

            decoded_id = decoded_id['id']
            self.connection_manager.store_connect(decoded_id, websocket)

            try:
                while True:
                    request = await websocket.receive()
                    self.log.debug(f"ORGIN - received request {request}")

                    if 'text' in request and request['text'] == 'ping':
                        await websocket.send_text("pong")
                        continue
                    
                    if request['type'] == 'websocket.disconnect':
                        raise WebSocketDisconnect
                    
                    request = json.loads(request['text'])

                    if self.encryption_enabled:
                        request = decode(request, self.server_secret)['data']

                    if not 'action' in request:
                        await websocket.send_json(
                            {"error": "missing expected input: 'action' "}
                        )
                        continue
                    action = request['action']
                    if not action in self.orgin:
                        await websocket.send_json(
                            {"error": f"no action {action} registered for orgin"}
                        )
                        continue
                    
                    executed_action =  self.orgin.run(
                        action,
                        request['args'] if 'args' in request else [],
                        request['kwargs'] if 'kwargs' in request else {},
                    )
                    self.log.debug(f"ORGIN action: {self.orgin[action]['config']['name']}")
                    if self.orgin[action]['config']['is_async']:
                        await websocket.send_json(
                            await executed_action
                        )
                    else:
                        await websocket.send_json(
                            executed_action
                        )
            except WebSocketDisconnect:
                self.connection_manager.disconnect(decoded_id)