import unittest
from qmoosa_runtime.deployment import prepare_sepolia_creation
class DeploymentTests(unittest.TestCase):
    def test_only_unsigned_zero_value_sepolia_plan_is_produced(self):
        item=prepare_sepolia_creation(sender="0x"+"11"*20,init_bytecode="0x6000",source_sha256="a"*64,gas_limit=100000)
        self.assertEqual(item["chainId"],11155111)
        self.assertFalse(item["deployed"])
        self.assertNotIn("to",item["transaction"])
        self.assertEqual(item["transaction"]["value"],"0x0")
    def test_missing_artifact_invalid_wallet_and_unbounded_gas_are_rejected(self):
        fixture=dict(sender="0x"+"11"*20,init_bytecode="0x6000",source_sha256="a"*64,gas_limit=100000)
        for key,value in [("sender","0x"+"00"*20),("init_bytecode","0x"),("init_bytecode","0x1"),("source_sha256","x"),("gas_limit",True),("gas_limit",10000001)]:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): prepare_sepolia_creation(**dict(fixture,**{key:value}))
if __name__=="__main__": unittest.main()
