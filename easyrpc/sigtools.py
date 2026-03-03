from __future__ import annotations
import enum
import importlib
import inspect
import json
import types
import typing
from typing import Any, Coroutine, get_args, get_origin


# -----------------------------
# JSON value codec (for defaults + Annotated metadata)
# -----------------------------

def encode_json_value(v: Any) -> dict:
    """JSON-safe codec that preserves tuple/list/dict distinctions."""
    if isinstance(v, enum.Enum):
        return {
            "k": "enum_member",
            "enum_type": {
                "module": v.__class__.__module__,
                "qualname": v.__class__.__qualname__,
            },
            "name": v.name,
        }
    if v is None or isinstance(v, (bool, int, float, str)):
        return {"k": "prim", "v": v}
    if isinstance(v, list):
        return {"k": "list", "v": [encode_json_value(x) for x in v]}
    if isinstance(v, tuple):
        return {"k": "tuple", "v": [encode_json_value(x) for x in v]}
    if isinstance(v, dict):
        # Restrict to string keys for JSON objects
        if not all(isinstance(k, str) for k in v):
            raise TypeError("Only dict defaults/metadata with string keys are supported")
        return {"k": "dict", "v": {k: encode_json_value(x) for k, x in v.items()}}
    raise TypeError(f"Value is not supported by this JSON codec: {v!r}")


def decode_json_value(spec: dict) -> Any:
    k = spec["k"]
    if k == "enum_member":
        cls = _import_qualname(spec["enum_type"]["module"], spec["enum_type"]["qualname"])
        return cls[spec["name"]]
    if k == "prim":
        return spec["v"]
    if k == "list":
        return [decode_json_value(x) for x in spec["v"]]
    if k == "tuple":
        return tuple(decode_json_value(x) for x in spec["v"])
    if k == "dict":
        return {k: decode_json_value(x) for k, x in spec["v"].items()}
    raise ValueError(f"Unknown JSON value kind: {k}")


# -----------------------------
# Defaults codec
# -----------------------------

def encode_default(v: Any) -> dict:
    if v is inspect._empty:
        return {"kind": "empty"}
    return {"kind": "value", "value": encode_json_value(v)}


def decode_default(spec: dict) -> Any:
    if spec["kind"] == "empty":
        return inspect._empty
    if spec["kind"] == "value":
        return decode_json_value(spec["value"])
    raise ValueError(f"Unknown default kind: {spec['kind']}")


# -----------------------------
# Type annotation codec (recursive)
# -----------------------------

def encode_type(tp: Any) -> dict:
    if tp is inspect._empty:
        return {"kind": "empty"}
    if tp is Any:
        return {"kind": "any"}
    if tp is Ellipsis:
        return {"kind": "ellipsis"}
    if tp is None or tp is type(None):
        return {"kind": "none"}

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is typing.Literal:
        return {
            "kind": "literal",
            "values": [encode_json_value(v) for v in args],
        }

    # Annotated[T, ...]
    if origin is typing.Annotated:
        base, *meta = args
        return {
            "kind": "annotated",
            "base": encode_type(base),
            "metadata": [encode_json_value(m) for m in meta],  # metadata must be JSON-able
        }

    # Union / Optional / PEP 604 unions (A | B)
    if origin is typing.Union or origin is types.UnionType:
        return {"kind": "union", "args": [encode_type(a) for a in args]}

    # Generic aliases e.g. list[int], dict[str, int], tuple[int, ...], Literal["x"]
    if origin is not None:
        return {
            "kind": "generic",
            "origin": encode_type(origin),
            "args": [encode_type(a) for a in args],
        }

    # Plain runtime classes/types
    if isinstance(tp, type):
        return {
            "kind": "type",
            "module": tp.__module__,
            "qualname": tp.__qualname__,
        }

    # Best effort for some typing/runtime objects that expose module+qualname
    mod = getattr(tp, "__module__", None)
    qn = getattr(tp, "__qualname__", None)
    if mod and qn:
        return {"kind": "type", "module": mod, "qualname": qn}

    raise TypeError(f"Unsupported annotation for JSON encoding: {tp!r}")


def _import_qualname(module_name: str, qualname: str) -> Any:
    mod = importlib.import_module(module_name)
    obj = mod
    for part in qualname.split("."):
        obj = getattr(obj, part)
    return obj


def decode_type(spec: dict) -> Any:
    kind = spec["kind"]

    if kind == "empty":
        return inspect._empty
    if kind == "any":
        return Any
    if kind == "ellipsis":
        return Ellipsis
    if kind == "none":
        return type(None)

    if kind == "literal":
        vals = [decode_json_value(v) for v in spec["values"]]
        return typing.Literal[tuple(vals)]  # type: ignore[index]

    if kind == "type":
        mod = spec["module"]
        qn = spec["qualname"]
        # builtins.NoneType may not be importable as attribute on builtins
        if mod == "builtins" and qn == "NoneType":
            return type(None)
        return _import_qualname(mod, qn)

    if kind == "annotated":
        base = decode_type(spec["base"])
        metadata = [decode_json_value(m) for m in spec["metadata"]]
        return typing.Annotated[base, *metadata]

    if kind == "union":
        items = [decode_type(a) for a in spec["args"]]
        if not items:
            raise ValueError("Union with no args is invalid")
        return typing.Union[tuple(items)]  # type: ignore[index]

    if kind == "generic":
        origin = decode_type(spec["origin"])
        args = tuple(decode_type(a) for a in spec["args"])
        return origin[args]

    raise ValueError(f"Unknown annotation kind: {kind}")


# -----------------------------
# Signature <-> JSON spec
# -----------------------------

def _encode_parameter(p: inspect.Parameter) -> dict:
    return {
        "name": p.name,
        "kind": p.kind.name,  # POSITIONAL_ONLY, VAR_POSITIONAL, etc.
        "default": encode_default(p.default),
        "annotation": encode_type(p.annotation),
    }


def _decode_parameter(d: dict) -> inspect.Parameter:
    return inspect.Parameter(
        name=d["name"],
        kind=getattr(inspect.Parameter, d["kind"]),
        default=decode_default(d["default"]),
        annotation=decode_type(d["annotation"]),
    )


def serialize_function_signature(fn: Any) -> dict:
    """
    Returns a JSON-serializable dict describing the function signature and annotations.
    """
    sig = inspect.signature(fn)

    # include_extras=True preserves Annotated metadata
    try:
        hints = typing.get_type_hints(fn, include_extras=True)
    except Exception:
        # Fallback if hints can't be resolved (e.g., unresolved forward refs)
        hints = getattr(fn, "__annotations__", {}) or {}

    params = []
    for p in sig.parameters.values():
        ann = hints.get(p.name, p.annotation)
        params.append(_encode_parameter(p.replace(annotation=ann)))

    ret_ann = hints.get("return", sig.return_annotation)

    return {
        "version": 1,
        "name": getattr(fn, "__name__", "anonymous"),
        "parameters": params,
        "return_annotation": encode_type(ret_ann),
        "doc": getattr(fn, "__doc__", "")
    }


def deserialize_signature(spec: dict) -> inspect.Signature:
    if spec.get("version") != 1:
        raise ValueError(f"Unsupported spec version: {spec.get('version')}")
    params = [_decode_parameter(p) for p in spec["parameters"]]
    ret = decode_type(spec["return_annotation"])
    return inspect.Signature(params, return_annotation=ret)


# -----------------------------
# Runtime type validation (common cases)
# -----------------------------

def _check_type(value: Any, tp: Any) -> bool:
    if tp is inspect._empty or tp is Any:
        return True
    if tp is None or tp is type(None):
        return value is None

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is typing.Annotated:
        # Validate against underlying type, ignore metadata for enforcement.
        return _check_type(value, args[0])

    if origin is typing.Union or origin is types.UnionType:
        return any(_check_type(value, a) for a in args)

    if origin is typing.Literal:
        return value in args

    if origin in (list, set, frozenset):
        if not isinstance(value, origin):
            return False
        (elem_t,) = args or (Any,)
        return all(_check_type(x, elem_t) for x in value)

    if origin is dict:
        if not isinstance(value, dict):
            return False
        key_t, val_t = args if args else (Any, Any)
        return all(_check_type(k, key_t) and _check_type(v, val_t) for k, v in value.items())

    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        # tuple[T, ...]
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_check_type(x, args[0]) for x in value)
        # tuple[T1, T2, ...]
        return len(value) == len(args) and all(_check_type(x, t) for x, t in zip(value, args))

    # Fallback for many parameterized generics: shallow isinstance(origin)
    if origin is not None:
        try:
            return isinstance(value, origin)
        except TypeError:
            return True  # unsupported runtime-check generic

    if isinstance(tp, type):
        return isinstance(value, tp)

    # Unknown/unsupported runtime-checkable annotation -> allow
    return True

def _coerce_value(value: Any, tp: Any) -> Any:
    origin = get_origin(tp)
    args = get_args(tp)

    if tp is inspect._empty or tp is Any:
        return value
    if tp is None or tp is type(None):
        if value is None:
            return None
        raise TypeError(f"Expected None, got {value!r}")

    if origin is typing.Annotated:
        return _coerce_value(value, args[0])

    if origin is typing.Union or origin is types.UnionType:
        last_err = None
        for a in args:
            try:
                return _coerce_value(value, a)
            except Exception as e:
                last_err = e
        raise TypeError(f"Value {value!r} does not match any Union option") from last_err

    if isinstance(tp, type) and issubclass(tp, enum.Enum):
        if isinstance(value, tp):
            return value
        try:
            return tp(value)  # converts "a" -> CustomEnum.a
        except Exception as e:
            raise TypeError(f"Invalid enum value {value!r} for {tp.__name__}") from e

    # fallback: no coercion, just return original
    if _check_type(value, tp):
        return value
    raise TypeError(f"Value {value!r} does not match {tp!r}")


# -----------------------------
# Rebuild a stub function with matching call-shape + validation
# -----------------------------

def create_proxy_from_spec(spec: dict, proxy: typing.Callable[..., Any] = None) -> typing.Callable[..., Any]:
    sig = deserialize_signature(spec['sig'])

    annotations = {
        p.name: p.annotation
        for p in sig.parameters.values()
        if p.annotation is not inspect._empty
    }
    if sig.return_annotation is not inspect._empty:
        annotations["return"] = sig.return_annotation

    # proxy.__name__ = spec.get("name", "stub")
    # proxy.__annotations__ = annotations
    # proxy.__signature__ = sig
    # proxy.__doc__ = spec.get("doc", "")

    def stub(*args, **kwargs):
        # Enforce same call signature rules (missing args, bad kwargs, etc.)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, value in list(bound.arguments.items()):
            p = sig.parameters[name]
            ann = p.annotation
            if ann is inspect._empty:
                continue

            if p.kind is inspect.Parameter.VAR_POSITIONAL:
                bound.arguments[name] = tuple(_coerce_value(x, ann) for x in value)
            elif p.kind is inspect.Parameter.VAR_KEYWORD:
                bound.arguments[name] = {k: _coerce_value(v, ann) for k, v in value.items()}
            else:
                bound.arguments[name] = _coerce_value(value, ann)

        result = proxy(*args, **kwargs)
        return result
        # if isinstance(result, Coroutine):
        #     return await result
        # return result

    stub.__name__ = spec.get("name", "stub")
    stub.__annotations__ = annotations
    # Helps inspect.signature(stub) report the reconstructed signature
    stub.__signature__ = sig
    stub.__doc__ = spec.get("doc", "")
    return stub


# -----------------------------
# Example
# -----------------------------
if __name__ == "__main__":
    from typing import Annotated, Optional, Union

    def original(
        a: int,
        /,
        b: Optional[Union[int, str]],
        *args: float,
        c: Annotated[list[int] | None, "meta"],
        d: tuple[int, ...] = (1, 2),
        **kw: int,
    ) -> Annotated[bool, "ret"]:
        return True

    # Store in a JSON field
    spec = serialize_function_signature(original)
    blob = json.dumps(spec)

    # Later...
    restored_spec = json.loads(blob)
    stub = create_proxy_from_spec(restored_spec)

    print(inspect.signature(stub))  # same displayed signature
    stub(1, "x", 1.0, 2.0, c=[1, 2], extra=3)  # OK

    try:
        stub(1, "x", c=["bad"])  # list[int] validation fails
    except TypeError as e:
        print("Validation error:", e)