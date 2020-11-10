from typing import Optional
from easyrpc.register import Generator, AsyncGenerator

class RpcGenerator:
    def __init__(self, generator):
        self.generator = generator
        self.started = False
    def start(self):
        if isinstance(self.generator, AsyncGenerator):
            async def generator():
                async for item in self.generator:
                    yield item
        else:
            async def generator():
                for item in self.generator:
                    yield item
        self.rpc_generator = generator()
        self.started = True
    async def next(self):
        if not self.started:
            self.start()
        try:
            return await self.rpc_generator.asend(None)
        except StopAsyncIteration:
            return 'GENERATOR_END'
    async def asend(self, message):
        return await self.next()