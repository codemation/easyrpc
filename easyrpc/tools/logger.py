from easyrpc.proxy import EasyRpcProxy

class EasyRpcProxyLogger(EasyRpcProxy):

    def __init__(self, *args, **kwargs):
        args = list(args)

        # override - default expects_results=True -> False -
        # logs do not expect return values
        args[8] = False
        super().__init__(*args, **kwargs)

    async def info(self, message):
        await self['info'](message)
    async def warning(self, message):
        await self['warning'](message)
    async def error(self, message):
        await self['error'](message)
    async def debugger(self, message):
        await self['debug'](message)
    async def exception(self, message):
        stack_trace = format_exc()
        await self['exception'](message, stack_trace)