## Namspacing

### PEP 20
!!! TIP "[PEP 20](https://www.python.org/dev/peps/pep-0020/)"
    Namespaces are one honking great idea -- let's do more of those!

!!! TIP 
    An EasyRpcServer can register functions in multiple namespaces, if unspecified 'Default' is used. 

```python
easy_server = await EasyRpcServer.create(
    server, 
    '/ws/easy', 
    server_secret='abcd1234'
)
```
### Registration
!!! TIP 
    Registration can be performed using the @decorator syntax or via easy_server.orgin(f, namespace='Namespace')

#### Decorator
```python
@easy_server.orgin # default
def foo(x):
    return x
@easy_server.orgin(namespace='Public')
def bar(x):
    return x
```

#### Register progamatically
```python
def foo(x):
    return x
easy_server.orgin(foo, namespace='private')
```