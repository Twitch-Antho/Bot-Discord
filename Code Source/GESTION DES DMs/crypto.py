# crypto.py
from cryptography.fernet import Fernet

# Générer une clé une seule fois et la garder secrète
# key = Fernet.generate_key()
KEY = b"TA_CLE_FERNET_ICI"  
fernet = Fernet(KEY)

def encrypt_log(message: str) -> bytes:
    return fernet.encrypt(message.encode())

def decrypt_log(data: bytes) -> str:
    return fernet.decrypt(data).decode()

def write_log(message: str, filepath="logs/dmshield_logs.enc"):
    encrypted = encrypt_log(message)
    with open(filepath, "ab") as f:
        f.write(encrypted + b"\n")
