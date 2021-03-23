## Key Features
- No predefined proxy functions at the remote endpoints
- Easily group and share functons among hosts / processes using Namespaces / Namespace Groups
- Proxy functions parameters are validated as if defined locally.
- Optional: pre-flight encyrption 
- No strict RPC message structure / size limit, within json serializable constraints

## Common Use Cases
- State sharing among forked workers 
- Shared Database connections / cache 
- Shared Queues
- Worker Pooling - Easy centralization for workers and distribution of work.  
- Function Chaining