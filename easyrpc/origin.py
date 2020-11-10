from easyrpc.register import ( 
    get_origin_register,
    get_signature_as_dict   
)


class Origin:
    def __init__(self, obj: object):
        self.obj = obj
        self._register = get_origin_register(obj)

    def __call__(self, func=None, namespace='DEFAULT'):
        """
        used to register function with a defined namespace
        """
        def register_in_namespace(func):
            namespaces = [namespace]
            if self.obj.kind == 'SERVER' and namespace in self.obj.namespace_groups:
                namespaces = list(self.obj.namespace_groups[namespace])
            for n_space in namespaces:
                self.obj.log.warning(f"ORIGIN - registered function {func.__name__} in {n_space} namespace")
                function = self._register(func, namespace=n_space)
            return function
        if not func:
            return register_in_namespace
        else:
            return register_in_namespace(func)

    def run(self, namespace, func, args=[], kwargs={}):
        """
        returns function called with given args & kwargs
        if type async, returns coroutine that should be awaited
        """
        if namespace in self.obj.namespaces:
            if func in self.obj.namespaces[namespace]:
                return self.obj.namespaces[namespace][func]['method'](
                    *args,
                    **kwargs
                )
        return None
    def get_registered_functions(self, namespace='DEFAULT'):
        return {'funcs': [{f: self.obj.namespace[f][config]} for f in self.obj.namespace]}

