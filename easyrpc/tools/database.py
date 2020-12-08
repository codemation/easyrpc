import asyncio
from easyrpc.proxy import EasyRpcProxy

class ProxyTable:
    def __init__(self, methods: dict):
        self.methods = methods
    def __getitem__(self, key_val):
        return self.methods['get_item'](key_val)
    async def set_item(self, key, values):
        return await self.methods['set_item'](key, values)
    async def get_schema(self):
        return await self.methods['get_schema']()
    async def insert(self, **kw):
        return await self.methods['insert'](**kw)
    async def update(self, where: dict = {}, **kw):
        if len(where) == 0 or not isinstance(where, dict):
            raise Exception(f"expected key-value for where")
        return await self.methods['update'](where=where, **kw)
    async def delete(self, where: dict = {}):
        if len(where) == 0 or not isinstance(where, dict):
            raise Exception(f"expected key-value for where")
    async def select(self, *args, **kw):
        return await self.methods['select'](*args, **kw)

class EasyRpcProxyDatabase(EasyRpcProxy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tables = dict()
    
        # create looping refresh_tables
        asyncio.create_task(self._cron_refresh_tables())
    async def show_tables(self):
        return await self['show_tables']()
    async def create_table(
        self, 
        name: str, 
        columns: list, 
        prim_key: str,
        **kw
        ):
        result = await self['create_table'](
            name=name, 
            columns=columns, 
            prim_key=prim_key,
            **kw
        )

        # refresh functions in namespace - instead of waiting on interval
        await self.get_all_registered_functions()

        # refresh local table reference with new functions
        await self.refresh_tables()
        
        return result

    async def run(self, query):
        return await self['run'](query)

    async def refresh_tables(self):
        self.tables = dict()
        tables = await self.show_tables()
    
        for table in tables:
            if not table in self.tables:
                table_methods = {}
                for method in {'insert', 'update', 'select', 'delete', 'get_schema', 'get_item', 'set_item'}:
                    table_methods[method] = self[f'{table}_{method}']
                self.tables[table] = ProxyTable(table_methods)
    async def _cron_refresh_tables(self):
        while True:
            try:
                await self.refresh_tables()
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    break
                self.log.exception(f"error during _cron_refresh_tables")
            await asyncio.sleep(10)