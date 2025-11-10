import random
import string
from fastapi import HTTPException
import secrets
import re
import json


class CustomError(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.message = message


def generate_random_string(size=32):
    random_string = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(size)])
    return random_string


def generate_ver_token():
    return 'ver_token_' + generate_random_string(128)


def generate_user_id():
    return 'user_' + generate_random_string(16)


def generate_thread_id():
    return 'thread_' + generate_random_string(16)


def generate_random_number():
    return str(random.randint(100000, 999999))


def generate_api_key():
    return 'na-sk-' + secrets.token_urlsafe(64)


def extract_json(raw: str):
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON found in model response.")
    return json.loads(match.group(0))


def extract_json_array(raw: str):
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON array found in model response.")
    return json.loads(match.group(0))
