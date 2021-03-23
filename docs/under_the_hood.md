## Under the hood 
### [fastapi](https://github.com/tiangolo/fastapi) 
for handling server side websocket communciation
### [aiohttp](https://github.com/aio-libs/aiohttp) 
ClientSessions for the client-side websocket communication,  
### [makefun](https://github.com/smarie/python-makefun) 
along with some standard library 'inspect' magic  for translating origin functions into proxy-useable functions with parameter validation, and lastly 
### [pyjwt](https://github.com/jpadilla/pyjwt) 
for authentication & encryption.

### Other Info
Registered functions are made available as callables which return co-routines and thus 'awaitable' to the remote-endpoints, this is true for both async and non-async registered functions. Due to this, the functions must be awaited within a running event_loop. When called, the input parameters are verified via the origin functions signature. 