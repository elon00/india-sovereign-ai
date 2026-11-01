"""Off-chain ML-KEM-768 / ML-DSA-65 using a pinned, local Node implementation.

Prototype memory-only keys. This is not a FIPS-validated module, a secure key
vault, authenticated peer identity, blockchain signing or on-chain PQC.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class SovereignPqcEngine:
    def __init__(self, nation_iso3: str):
        if not isinstance(nation_iso3, str) or not re.fullmatch(r"[A-Z]{3}", nation_iso3):
            raise ValueError("A three-letter uppercase project label is required")
        self.nation_iso3 = nation_iso3
        self.algorithm_kem = "ML-KEM-768"
        self.algorithm_dsa = "ML-DSA-65"
        self._kem_secret = None
        self._dsa_secret = None
        self._closed = False

    def _call(self, operation, **fields):
        if self._closed:
            raise RuntimeError("Engine is closed")
        executable = shutil.which("node")
        if not executable:
            raise RuntimeError("Node.js 22+ and npm ci are required for the PQC backend")
        request = json.dumps(dict(operation=operation, **fields))
        if len(request.encode()) > 131072:
            raise ValueError("PQC request exceeds its size limit")
        try:
            result = subprocess.run([executable, str(ROOT / "src/pqc_backend.mjs")], input=request,
                capture_output=True, text=True, encoding="utf-8", timeout=20, cwd=ROOT)
            if result.returncode or len(result.stdout) > 131072:
                raise RuntimeError("PQC backend unavailable or rejected the request; install locked dependencies with npm ci")
            return json.loads(result.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            raise RuntimeError("PQC backend unavailable; no cryptographic success was established") from None

    @staticmethod
    def _hex(value, size):
        if not isinstance(value, str) or len(value) != size*2 or not re.fullmatch(r"[0-9a-fA-F]+", value):
            raise ValueError("Invalid hexadecimal cryptographic field length or encoding")
        return value

    @staticmethod
    def _message(value):
        if not isinstance(value, bytes) or len(value) > 16384:
            raise ValueError("Message must be bytes with at most 16384 bytes")
        return value.hex()

    def generate_sovereign_keypair(self):
        if self._closed:
            raise RuntimeError("Engine is closed")
        if self._kem_secret is not None or self._dsa_secret is not None:
            raise RuntimeError("Use a new engine for explicit ephemeral key rotation")
        result = self._call("keygen")
        self._kem_secret = bytearray.fromhex(self._hex(result["kemSecret"], 2400))
        self._dsa_secret = bytearray.fromhex(self._hex(result["dsaSecret"], 4032))
        return {"nation": self.nation_iso3, "kem": self.algorithm_kem, "dsa": self.algorithm_dsa,
            "public_key_hex": self._hex(result["kemPublic"], 1184),
            "signing_public_key_hex": self._hex(result["dsaPublic"], 1952),
            "assurance": "OFFCHAIN_LIBRARY_IMPLEMENTATION_NOT_FIPS_MODULE_VALIDATION"}

    def encapsulate_secret(self, peer_public_key):
        result = self._call("encapsulate", publicKey=self._hex(peer_public_key, 1184))
        return {"ciphertext_hex": self._hex(result["cipherText"], 1088),
            "shared_secret_hex": self._hex(result["sharedSecret"], 32),
            "status": "OFFCHAIN_ML_KEM_768_ENCAPSULATION"}

    def decapsulate_secret(self, ciphertext):
        if self._kem_secret is None:
            raise RuntimeError("Generate keys before decapsulation")
        result = self._call("decapsulate", cipherText=self._hex(ciphertext, 1088), secretKey=self._kem_secret.hex())
        return bytes.fromhex(self._hex(result["sharedSecret"], 32))

    def sign_message(self, message):
        if self._dsa_secret is None:
            raise RuntimeError("Generate keys before signing")
        result = self._call("sign", message=self._message(message), secretKey=self._dsa_secret.hex())
        return bytes.fromhex(self._hex(result["signature"], 3309))

    def verify_signature(self, signature, message, public_key):
        try:
            signature_hex = self._hex(signature.hex() if isinstance(signature, bytes) else signature, 3309)
            message_hex = self._message(message)
            public_key_hex = self._hex(public_key, 1952)
        except ValueError:
            return False
        return self._call("verify", signature=signature_hex, message=message_hex, publicKey=public_key_hex)["valid"] is True

    def close(self):
        for value in (self._kem_secret, self._dsa_secret):
            if value is not None:
                value[:] = b"\x00" * len(value)
        self._closed = True
        # Best-effort clearing only: Python/JS/JSON may have made other copies.
