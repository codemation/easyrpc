from typing import Literal, Union, Optional
from enum import Enum
from click import Tuple
from fastapi import FastAPI
from easyrpc.server import EasyRpcServer

server = FastAPI()

# @server.on_event('startup')
# async def setup():
math_server = EasyRpcServer(
    server, 
    '/ws/core', 
    server_secret='abcd1234'
)

@math_server.origin(namespace='basic_math')
async def add(a: int, b: int):
    return a + b

@math_server.origin(namespace='basic_math')
async def subtract(a, b):
    return a-b

@math_server.origin(namespace='basic_math')
async def divide(a, b):
    return a / b

@math_server.origin(namespace='basic_math')
async def compare(a, b):
    return a == b

@math_server.origin(namespace='core')
async def get_dict(a, b, c):
    return {a: a, b: b, c: c}

@math_server.origin(namespace='core')
async def get_list(a, b, c):
    return [a, b, c]

@math_server.origin(namespace='core')
async def complex(obj):
    return obj

@math_server.origin(namespace='core')
async def annotations(a: int, b: Literal['a', 'b', 'c'], c: list, d: Optional[str] = None) -> Tuple:
    return a, b, c, d

class CustomEnum(str, Enum):
    a = 'a'
    b = 'b'
    c = 'c'
@math_server.origin(namespace='core')
async def enum_test(e: CustomEnum) -> str:
    return e

# generator
class Data:
    a: int = 1
    b: float = 2.0
    c: bool = False
    d: list = [1,2,3]

@math_server.origin(namespace='core')
async def generator():
    data = Data()
    yield data.a
    yield data.b
    yield data.c
    yield data.d
@math_server.origin(namespace='core')
async def generate_objects(*args):
    for object in args:
        yield object
