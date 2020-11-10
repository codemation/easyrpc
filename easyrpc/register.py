from inspect import (
    signature, 
    Signature, 
    FullArgSpec, 
    getfullargspec, 
    Parameter, 
    _empty,
    _ParameterKind, 
    _PARAM_NAME_MAPPING,
    iscoroutinefunction
)
from copy import deepcopy
from collections import OrderedDict
from makefun import create_function
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
    async def __proxy__(*args, **kwargs):
        result = proxy(*args, **kwargs)
        if isinstance(result, Coroutine):
            return await result
        return result

    #__proxy__.__name__ = f"{config['name']}_proxy"
    __proxy__.__name__ = f"{config['name']}"
    nf = create_function(
        create_signature_from_dict(
            config['sig']
        ),
        __proxy__
    )

    return nf
def create_signature_from_dict(func_sig: dict):
    """
    contstruct a function signature from dict
    config, created via get_signature_as_dict
    """
    sig_dict = deepcopy(func_sig)

    params_od = OrderedDict()
    for k in list(sig_dict.keys()):
        for pk in list(sig_dict[k].keys()):
            sig_dict[k][pk]['kind'] = _ParameterKind.__dict__[sig_dict[k][pk]['kind']]

            name, kind = sig_dict[k][pk]['name'], sig_dict[k][pk]['kind']
            default_or_annotations = {}
            for config in ('default', 'annotation'):
                if config == 'annotation':
                    continue
                if config in  sig_dict[k][pk]:
                    default_or_annotations[config] = sig_dict[k][pk][config]

            if len(default_or_annotations) > 0:
                params_od[pk] = Parameter(name, _ParameterKind(kind), **default_or_annotations)
            else:
                params_od[pk] = Parameter(name, _ParameterKind(kind))

    list_of_params = [v for k,v in params_od.items()]
    return Signature(list_of_params)

def get_signature_as_dict(f):
    """
    dictify a function signature so it can be 
    applied to a proxy function
    """
    sig = signature(f)
    pars = sig.parameters

    pars_dict = {}
    for par, par_item in pars.items():
        pars_dict[par] = {}
        pars_dict[par]['name'] = par_item._name
        pars_dict[par]['kind'] = par_item._kind.name
        if not par_item._default is _empty:
            pars_dict[par]['default'] = par_item._default
        if not par_item._annotation is _empty:
            pars_dict[par]['annotation'] = str(par_item._annotation)
    return {f.__name__: pars_dict}

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
                'sig': get_signature_as_dict(f),
                'name': f.__name__,
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

