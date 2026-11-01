"""Actual local component checks; no 100/100 or deployment certification."""
import hmac
import subprocess
import unittest
from unittest.mock import patch
from src.sovereign_core import SovereignNode
from src.pqc_layer import SovereignPqcEngine
from src.conway_consensus import ConwayConsensusGrid
from src.x402_telemetry import X402SovereignGateway


class PrototypeTests(unittest.TestCase):
    def node(self):
        return SovereignNode("India","IN","IND","New Delhi","South Asia")

    def test_initialization_does_not_claim_network_liveness(self):
        self.assertEqual(self.node().status,"LOCAL_SIMULATION_ONLY")

    def test_identifier_uses_full_input_and_makes_no_zk_or_onchain_claim(self):
        node=self.node()
        first=node.create_citizen_did("a"*64)
        second=node.create_citizen_did("a"*63+"b")
        self.assertNotEqual(first["local_identifier"],second["local_identifier"])
        self.assertFalse(first["zero_knowledge_proof"])
        self.assertFalse(first["onchain"])
        self.assertNotIn("pedersen_commitment",first)

    def test_malformed_identifiers_are_rejected(self):
        for value in (None,"","0"*32,"z"*64):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.node().create_citizen_did(value)

    def test_unconfigured_settlement_cannot_move_epoch_or_claim_payment(self):
        node=self.node();old=node.epoch
        with self.assertRaises(NotImplementedError):
            node.execute_sovereign_settlement("USA",100,"test")
        self.assertEqual(node.epoch,old)

    def test_simulation_uses_integer_base_units_and_is_not_a_transaction(self):
        node=self.node();receipt=node.simulate_settlement("USA",100,"test")
        self.assertEqual(receipt["status"],"LOCAL_SIMULATION_NOT_SETTLED")
        self.assertFalse(receipt["onchain"])
        self.assertNotIn("tx_hash",receipt)
        for value in (0,-1,True,1.5,float("nan"),float("inf"),2**256):
            with self.subTest(value=value),self.assertRaises(ValueError):
                node.simulate_settlement("USA",value,"test")

    def test_formatted_and_empty_payment_proofs_do_not_authorize_access(self):
        gateway=X402SovereignGateway("IND")
        for proof in ("a"*64,"0"*64,"",None,{},"signed-looking-proof"):
            self.assertFalse(gateway.verify_payment_proof(proof))
        challenge=gateway.generate_payment_challenge("/telemetry")
        self.assertEqual(challenge["status"],503)
        self.assertNotIn("protocol",challenge)

    def test_invalid_resource_path_is_rejected(self):
        for path in (None,"","telemetry"):
            with self.subTest(path=path),self.assertRaises(ValueError):
                X402SovereignGateway("IND").generate_payment_challenge(path)


class ConwayTests(unittest.TestCase):
    def test_glider_moves_after_four_generations(self):
        engine=ConwayConsensusGrid()
        for _ in range(4):self.assertEqual(engine.step(),5)
        actual={(r,c) for r in range(8) for c in range(8) if engine.grid[r][c]}
        self.assertEqual(actual,{(2,3),(3,4),(4,2),(4,3),(4,4)})

    def test_still_life_and_blinker(self):
        engine=ConwayConsensusGrid();engine.grid=[[0]*8 for _ in range(8)]
        for r,c in ((2,2),(2,3),(3,2),(3,3)):engine.grid[r][c]=1
        before=[row[:] for row in engine.grid]
        self.assertEqual(engine.step(),4);self.assertEqual(engine.grid,before)
        engine.grid=[[0]*8 for _ in range(8)]
        for c in (2,3,4):engine.grid[3][c]=1
        before=[row[:] for row in engine.grid]
        engine.step();self.assertNotEqual(engine.grid,before)
        engine.step();self.assertEqual(engine.grid,before)

    def test_small_invalid_and_oversized_dimensions_rejected(self):
        for width,height in ((0,8),(3,8),(257,8),(True,8),(8,2)):
            with self.subTest(width=width,height=height),self.assertRaises(ValueError):
                ConwayConsensusGrid(width,height)


class RealPqcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.alice=SovereignPqcEngine("IND");cls.bob=SovereignPqcEngine("USA")
        cls.alice_public=cls.alice.generate_sovereign_keypair()
        cls.bob_public=cls.bob.generate_sovereign_keypair()

    @classmethod
    def tearDownClass(cls):
        cls.alice.close();cls.bob.close()

    def test_public_key_metadata_contains_real_lengths_and_no_private_keys(self):
        public=self.alice_public
        self.assertEqual(len(bytes.fromhex(public["public_key_hex"])),1184)
        self.assertEqual(len(bytes.fromhex(public["signing_public_key_hex"])),1952)
        self.assertFalse(any("secret" in key or "private" in key for key in public))
        self.assertIn("NOT_FIPS_MODULE_VALIDATION",public["assurance"])

    def test_real_kem_roundtrip(self):
        result=self.bob.encapsulate_secret(self.alice_public["public_key_hex"])
        recovered=self.alice.decapsulate_secret(result["ciphertext_hex"])
        self.assertEqual(len(recovered),32)
        self.assertTrue(hmac.compare_digest(recovered,bytes.fromhex(result["shared_secret_hex"])))

    def test_kem_tamper_and_wrong_key_yield_different_secrets(self):
        result=self.bob.encapsulate_secret(self.alice_public["public_key_hex"])
        secret=bytes.fromhex(result["shared_secret_hex"])
        altered=bytearray.fromhex(result["ciphertext_hex"]);altered[7]^=1
        self.assertFalse(hmac.compare_digest(self.alice.decapsulate_secret(altered.hex()),secret))
        self.assertFalse(hmac.compare_digest(self.bob.decapsulate_secret(result["ciphertext_hex"]),secret))

    def test_real_signature_rejects_wrong_message_key_and_mutation(self):
        message=b"country-token-test-message"
        signature=self.alice.sign_message(message)
        self.assertEqual(len(signature),3309)
        self.assertTrue(self.alice.verify_signature(signature,message,self.alice_public["signing_public_key_hex"]))
        self.assertFalse(self.alice.verify_signature(signature,message+b"altered",self.alice_public["signing_public_key_hex"]))
        self.assertFalse(self.alice.verify_signature(signature,message,self.bob_public["signing_public_key_hex"]))
        altered=bytearray(signature);altered[4]^=1
        self.assertFalse(self.alice.verify_signature(bytes(altered),message,self.alice_public["signing_public_key_hex"]))

    def test_malformed_crypto_fields_are_rejected(self):
        for public in (None,"","a"*64,"zz"*1184):
            with self.subTest(public_type=type(public).__name__),self.assertRaises(ValueError):
                self.alice.encapsulate_secret(public)
        self.assertFalse(self.alice.verify_signature(b"",b"message",self.alice_public["signing_public_key_hex"]))

    def test_key_lifecycle_blocks_use_before_generation_and_after_close(self):
        engine=SovereignPqcEngine("IND")
        with self.assertRaises(RuntimeError):engine.sign_message(b"test")
        with self.assertRaises(RuntimeError):engine.decapsulate_secret("a"*2176)
        engine.generate_sovereign_keypair()
        with self.assertRaises(RuntimeError):engine.generate_sovereign_keypair()
        engine.close()
        self.assertTrue(all(value==0 for value in engine._kem_secret))
        with self.assertRaises(RuntimeError):engine.generate_sovereign_keypair()

    def test_backend_errors_do_not_expose_request_or_secret_text(self):
        failure=subprocess.CompletedProcess([],1,stdout="",stderr="secret-canary-not-a-real-key")
        with patch("src.pqc_layer.subprocess.run",return_value=failure):
            with self.assertRaises(RuntimeError) as result:self.alice._call("keygen")
        self.assertNotIn("secret-canary",str(result.exception))


if __name__=="__main__":unittest.main()
