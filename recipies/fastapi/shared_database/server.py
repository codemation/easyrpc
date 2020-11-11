from easyrpc.proxy import EasyRpcProxy
from fastapi import FastAPI
from aiopyql.data import Database

server = FastAPI()

@server.on_event('startup')
async def setup():
    server.data = {}

    server.data['keystore'] = await EasyRpcProxy.create(
        '0.0.0.0', 
        8220, 
        '/ws/database', 
        server_secret='abcd1234',
        namespace='keystore'
    )    

@server.post("/{table}")
async def insert_or_update_table(table, data: dict):
    for key, value in data.items():
        if await server.data['keystore']['select']('*', where={'key': key}) == []:
            await server.data['keystore']['insert'](
                key=key,
                value=value
            )
        else:
            await server.data['keystore']['update'](
                value=value,
                where={'key': key}
            )

@server.get("/{table}")
async def get_table_items(table: str):
    return await server.data['keystore']['select']('*')

@server.delete("/{table}")
async def delete_table_item(table: str, where: dict):
    return await server.data['keystore']['delete'](**where)