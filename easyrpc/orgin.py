from easyrpc.register import ( 
    get_orgin_register,
    get_signature_as_dict   
)
class Orgin:
    def __init__(self, obj: object):
        self.obj = obj
        self._register = get_orgin_register(obj)
        self(self.get_registered_functions)
    def __call__(self, func):
        self.obj.log.warning(f"ORGIN - registered function {func.__name__} ")
        return self._register(func)
    def __contains__(self, func):
        return func in self.obj.ws_rpcs
    def __getitem__(self, func):
        if func in self:
            return self.obj.ws_rpcs[func]
    def __iter__(self):
        def get_config():
            for f in self.obj.ws_rpcs:
                yield {f: self.obj.ws_rpcs[f]['config']}
        return get_config()
    def run(self, func, args=[], kwargs={}):
        """
        returns function called with given args & kwargs
        if type async, returns coroutine that should be awaited
        """
        if func in self:
            return self[func]['method'](
                *args,
                **kwargs
            )
        return None
    def get_registered_functions(self):
        return {'funcs': [func for func in self]}

