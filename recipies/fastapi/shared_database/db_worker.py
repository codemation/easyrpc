import uuid, random
import asyncio
import logging

from easyrpc.server import EasyRpcServer
from fastapi import FastAPI
from aiopyql.data import Database

server = FastAPI()
log = logging.getLogger('uvicorn')
server.event_loop = asyncio.get_event_loop()

@server.on_event('startup')
async def db_setup():

    db_server = await EasyRpcServer.create(server, '/ws/database', server_secret='abcd1234')

    db = await Database.create(
        database='easy_db', 
        loop=server.event_loop, 
        cache_enabled=True
    )
    if not 'keystore' in db.tables:
        await db.create_table(
            'keystore',
            [
                ('key', str, 'UNIQUE NOT NULL'),
                ('value', str)
            ],
            'key',
            cache_enabled=True
        )
    server.data = {}
    server.data['keystore'] = db
        
    # register each func table namespace 
    for table in db.tables:
        for func in {'select', 'update', 'insert', 'delete'}:
            db_server.origin(getattr(db.tables[table], func),namespace=table)
    server.db_server = db_server


@server.on_event('shutdown')
async def shutdown():
    await server.data['keystore'].close()

