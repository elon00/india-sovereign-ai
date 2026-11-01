"""Unconfigured payment boundary; formatted hashes are not payment evidence."""


class X402SovereignGateway:
    status = "PAYMENT_BACKEND_NOT_CONFIGURED"

    def __init__(self, nation_iso3: str):
        self.nation_iso3 = nation_iso3

    def generate_payment_challenge(self, resource_path: str):
        if not isinstance(resource_path, str) or not resource_path.startswith("/"):
            raise ValueError("A resource path is required")
        # No fabricated x402 version, nonce, Bitcoin amount or recipient address.
        return {"status": 503, "resource": resource_path, "code": self.status}

    def verify_payment_proof(self, proof_hash):
        return False
