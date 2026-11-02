"""Prepare unsigned Sepolia contract creation; never sign, send or fund it."""
import hashlib
import re
from .chain import fixed_hex

def prepare_sepolia_creation(*, sender, init_bytecode, source_sha256, gas_limit):
    sender = fixed_hex(sender,20)
    if sender == "0x"+"00"*20:
        raise ValueError("A nonzero public wallet address is required")
    if not isinstance(init_bytecode,str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2}){1,49152}",init_bytecode):
        raise ValueError("Compiled init bytecode is required, at most 49152 bytes")
    if not isinstance(source_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",source_sha256):
        raise ValueError("A reviewed source SHA-256 is required")
    if type(gas_limit) is not int or not 21000 <= gas_limit <= 10000000:
        raise ValueError("Explicit bounded gas limit required")
    return {"status":"UNSIGNED_REQUIRES_WALLET_REVIEW","network":"Ethereum Sepolia","chainId":11155111,
            "transaction":{"from":sender,"chainId":"0xaa36a7","value":"0x0","data":init_bytecode,"gas":hex(gas_limit)},
            "sourceSha256":source_sha256,"initBytecodeSha256":hashlib.sha256(bytes.fromhex(init_bytecode[2:])).hexdigest(),
            "sourceBytecodeMatch":"NOT_ESTABLISHED","gasEstimated":False,"signed":False,"submitted":False,"deployed":False}
