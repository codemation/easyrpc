class ServerConnectionError(Exception):
    def __init__(self, server, port):
        super().__init__(
            self,
            f"Proxy -> Server connection error: server {server} - port: {port}"
        )
class ServerUnreachable(Exception):
    def __init__(self, server, port):
        super().__init__(
            self,
            f"Proxy -> Server unreachable: server {server} - port: {port}"
        )

# exceptions that will allow proxy to retry
KNOWN_EXCEPTIONS = (
    ServerUnreachable,
    ServerConnectionError
)