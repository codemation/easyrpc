import asyncio
import os, time
import pytest
import subprocess, signal
from easyrpc.proxy import EasyRpcProxy

class SomethingComplex:
    test: int = 'test'
    also: dict = {'a': 1}

SERVER = '0.0.0.0'
SERVER_PORT = 8320
MODULE = 'tests.core'

def server_manager():
    """
    starts uvicorn server for testing, and cleans up once finished
    """
    p = subprocess.Popen(
        f"uvicorn --host {SERVER} --port {SERVER_PORT} {MODULE}:server".split(' ')
    )
    time.sleep(5)
    yield p
    p.send_signal(
        signal.SIGTERM
    )
    print(f"pid is {p.pid}")
    p.wait()

@pytest.fixture
def manager():
    yield from server_manager()


@pytest.mark.asyncio
async def test_core_functionality(manager):
    await asyncio.sleep(5)
    # create basic proxy - call methods
    proxy = await EasyRpcProxy.create(
        SERVER, 
        SERVER_PORT, 
        '/ws/core', 
        server_secret='abcd1234',
        namespace='basic_math'
    )
    
    # basic function usage
    
    # int
    assert await proxy['add'](1,2) == 1 + 2 , f"expected sum result of {1+2}"

    assert await proxy['subtract'](6,1) == 6-1, f"expected subtract result of {6-1}"
    
    # float
    assert await proxy['divide'](2,3) == 2/3, f"expected divide result of {2/3}"

    # bool
    assert await proxy['compare']('a', 'a'), f"should be equal"

    core = await EasyRpcProxy.create(
        SERVER, 
        SERVER_PORT, 
        '/ws/core', 
        server_secret='abcd1234',
        namespace='core'
    )

    # dict
    result = await core['get_dict']('a', 'b', 'c')
    expected = {'a': 'a', 'b': 'b', 'c': 'c'}
    assert result == {'a': 'a', 'b': 'b', 'c': 'c'}, f"expected values - {expected}"

    # list
    result = await core['get_list']('a', 'b', 'c')
    assert result == ['a', 'b', 'c'], f"expected result of {['a', 'b', 'c']}"

    something = SomethingComplex()

    # object
    result = await core['complex'](something)
    assert result.test == something.test, f"expected result something.test of {something.test}"
    assert result.also == something.also, f"expected result something.test of {something.also}"

    # test generator
    data = [d async for d in await core['generator']()]
    assert data[0] == 1, f"expected 1"
    assert data[1] == 2.0, f"expected 2.0"
    assert data[2] == False, f"expected {False}"
    assert data[3] == [1,2,3], f"expected {[1,2,3]}"

    # objects & generators

    objects = [obj async for obj in await core['generate_objects'](
        SomethingComplex(), SomethingComplex(), SomethingComplex()
    )]
    for obj in objects:
        assert isinstance(obj, SomethingComplex), f'expected object is of type SomethingComplex'
        assert obj.test == 'test', f"expected 'test'"
        assert obj.also == {'a': 1}, f"expected {{'a': 1}}"

    # core & annotations
    result = await core['annotations'](1, 'a', [1,2,3])

    assert result[0] == 1, f"expected 1"
    assert result[1] == 'a', f"expected 'a'"
    assert result[2] == [1,2,3], f"expected {[1,2,3]}"
    assert result[3] == None, f"expected None"

    # bad input
    with pytest.raises(TypeError):
        await core['annotations']('a', 'd', (1,2,3))

    with pytest.raises(TypeError):
        await core['annotations'](1, 'd', (1,2,3))

    with pytest.raises(TypeError):
        await core['annotations'](1, 'c', (1,2,3))
    
    # enum test
    assert await core['enum_test']('a') == 'a', f"expected 'a'"
    assert await core['enum_test']('b') == 'b', f"expected 'b'"
    assert await core['enum_test']('c') == 'c', f"expected 'c'"

    with pytest.raises(TypeError):
        await core['enum_test']('f')