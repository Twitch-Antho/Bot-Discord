# crypto.py
from cryptography.fernet import Fernet
from config import FERNET_KEY, LOG_FILE

fernet = Fernet(FERNET_KEY)

def encrypt_log(message: str) -> bytes:
    return fernet.encrypt(message.encode())

def decrypt_log(data: bytes) -> str:
    return fernet.decrypt(data).decode()

def write_log(message: str):
    encrypted = encrypt_log(message)
    with open(LOG_FILE, "ab") as f:
        f.write(encrypted + b"\n")

def read_logs():
    logs = []
    try:
        with open(LOG_FILE, "rb") as f:
            for line in f:
                if line.strip():
                    logs.append(decrypt_log(line.strip()))
    except FileNotFoundError:
        pass
    return logs
