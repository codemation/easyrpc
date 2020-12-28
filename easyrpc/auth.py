import os, uuid, time, json, base64, jwt, string, random

def encode(secret, log=None, **kw):
    try:
        return jwt.encode(kw, secret, algorithm='HS256')
    except Exception as e:
        if log:
            log.exception(f"error encoding {kw} using {secret}")

def decode(token, secret, log=None):
    try:
        return jwt.decode(token, secret, algorithms='HS256')
    except Exception as e:
        if log:
            log.exception(f"error decoding token {token} using {secret}")