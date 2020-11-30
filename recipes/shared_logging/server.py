from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

import logging

logging.basicConfig()

server = FastAPI()

@server.on_event('startup')
async def setup():
    server.rpc = EasyRpcServer(server, '/ws/logger', server_secret='abcd1234')

    @server.rpc.origin(namespace='logger')
    def info(message):
        logging.info(message)
    
    @server.rpc.origin(namespace='logger')
    def warning(message):
        logging.warning(message)

    @server.rpc.origin(namespace='logger')
    def error(message):
        logging.error(message)

    @server.rpc.origin(namespace='logger')
    def debug(message):
        logging.debug(message)
    
    @server.rpc.origin(namespace='logger')
    def exception(message, traceback):
        try:
            raise Exception(traceback)
        except Exception:
            logging.exception(message)