"""Country-themed local simulation. No government identity, ZK proof or ledger settlement."""
import hashlib
import json
import re


class SovereignNode:
    def __init__(self, country_name, iso2, iso3, capital, region):
        if not isinstance(iso3, str) or not re.fullmatch(r"[A-Z]{3}", iso3):
            raise ValueError("A three-letter project label is required")
        self.country_name, self.iso2, self.iso3 = country_name, iso2, iso3
        self.capital, self.region = capital, region
        self.state_root = hashlib.sha256(json.dumps([iso3,country_name,"prototype-genesis"]).encode()).hexdigest()
        self.status = "LOCAL_SIMULATION_ONLY"
        self.epoch = 1

    def create_citizen_did(self, national_id_hash):
        """Legacy method name. Returns a local identifier, not an authenticated DID or ZK credential."""
        if not isinstance(national_id_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", national_id_hash):
            raise ValueError("An opaque 32-byte hexadecimal test identifier is required")
        digest = hashlib.sha256(json.dumps([self.iso3,national_id_hash.lower()]).encode()).hexdigest()
        return {"local_identifier": "urn:qmoosa:prototype:"+self.iso3.lower()+":"+digest,
                "commitment_sha256": digest, "status": "LOCAL_IDENTIFIER_NOT_AUTHENTICATED",
                "zero_knowledge_proof": False, "onchain": False}

    def execute_sovereign_settlement(self, counterparty_iso3, amount_sdr, purpose):
        raise NotImplementedError("No signed and confirmed blockchain settlement backend is configured")

    def simulate_settlement(self, counterparty_iso3, amount_base_units, purpose):
        if (not isinstance(counterparty_iso3, str) or not re.fullmatch(r"[A-Z]{3}",counterparty_iso3)
                or type(amount_base_units) is not int or not 0 < amount_base_units < 2**256
                or not isinstance(purpose,str) or not purpose.strip() or len(purpose)>256):
            raise ValueError("Simulation requires a project label, positive bounded integer base units and purpose")
        self.epoch += 1
        receipt = {"source":self.iso3,"counterparty":counterparty_iso3,"amount_base_units":amount_base_units,
                   "purpose":purpose,"epoch":self.epoch,"status":"LOCAL_SIMULATION_NOT_SETTLED","onchain":False}
        receipt["simulation_id"] = hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest()
        return receipt
