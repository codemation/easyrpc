import os, uuid, time, json, base64, jwt, string, random

def encode(secret, **kw):
    try:
        return jwt.encode(kw, secret, algorithm='HS256').decode()
    except Exception as e:
        print(repr(e))
        print(f"error encoding {kw} using {secret}")

def decode(token, secret):
    try:
        return jwt.decode(token.encode('utf-8'), secret, algorithm='HS256')
    except Exception as e:
        print(f"error decoding token {token} using {secret}")