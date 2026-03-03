from inspect import (
    iscoroutinefunction
)

from easyrpc.sigtools import serialize_function_signature, create_proxy_from_spec
from typing import Callable

async def coro():
    pass
async def async_gen():
    yield None
c = coro()
Coroutine = type(c)

c.close()
Generator = type(i for i in ())

ag = async_gen()
AsyncGenerator = type(ag)
async_generator_asend = type(ag.asend(None))


def create_proxy_from_config(config: dict, proxy: Callable):
    """
    input:
        `config` created by get_signature_as_dict() on function origin
    
    Will be run on proxy host to create a function matching signature of 
    origin function and hides away the websocket rpc logic calling function
    on origin 
    """
    return create_proxy_from_spec(config, proxy=proxy)


def get_origin_register(obj: object):
    """
    input:
        `obj` will be assigned .namespace dictionary 
        which will be used to store registered functions on
        an origin node
    """
    def register(f, namespace):
        if not namespace in obj.namespaces:
            obj.namespaces[namespace] = {}
        if not f.__name__ in obj.namespaces[namespace]:
            obj.namespaces[namespace][f.__name__] = {}
            obj.namespaces[namespace][f.__name__]['config'] = {
                'sig': serialize_function_signature(f),
                'name': f.__name__,
                'doc': f.__doc__,
                'is_async': iscoroutinefunction(f)
            }
            obj.namespaces[namespace][f.__name__]['method'] = f
        return f
    return register


if __name__ == '__main__':
    class Special:
        pass
    s = Special()

    register = get_origin_register(s)
            
    @register
    def a(a: str, b: str, c: int = 0):
        print(f"{a} {b} {c}")
        return "a"

    @register
    def b(a, b, c=0):
        print("b")
        return "b"

    @register
    def c(a, b, c=0, **kw):
        print("c")
        return "c"

    def norm_deco(f):
        def deco(*args, **kwargs):
            return f(*args, **kwargs)
        return deco

    @register
    async def d(a, b, **kw):
        return a, b, c

    print(f"## RPCS CONIG ##  {s.ws_rpcs}")


    import asyncio

    async def parse(**kwargs):
        for k,v in kwargs.items():
            print(k)
    func_from_config = create_proxy_from_config(s.ws_rpcs['d']['config'], parse)
    #help(func_from_config)
    asyncio.run(func_from_config(1, 2, test={'a': 'dict'}))
    #func_from_config(1, 2, test={'a': 'dict'})

