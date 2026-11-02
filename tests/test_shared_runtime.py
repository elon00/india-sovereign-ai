import io
import json
import unittest
from unittest.mock import patch
from qmoosa_runtime.ai import GeminiPlanner, IntegrationError
from qmoosa_runtime.chain import EvmReader, quantity
from qmoosa_runtime.quantum import solve_qubo

ADDRESS = "0x" + "11"*20
HASH = "0x" + "22"*32
OTHER = "0x" + "33"*32

class RuntimeTests(unittest.TestCase):
    def planner(self, **options):
        return GeminiPlanner(api_key="test-placeholder",models=["model-a","model-b"],**options)

    def test_disabled_ai_makes_no_request(self):
        with patch("qmoosa_runtime.ai.build_opener") as opener:
            with self.assertRaises(IntegrationError): self.planner().plan("hello",model="model-a")
            opener.assert_not_called()

    def test_allowlisted_model_and_advisory_text(self):
        response={"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"a plan"}]}}]}
        with patch("qmoosa_runtime.ai.build_opener") as opener:
            opener.return_value.open.return_value=io.BytesIO(json.dumps(response).encode())
            planner=self.planner(enabled=True)
            result=planner.plan("hello",model="model-b")
            self.assertEqual(result["text"],"a plan")
            self.assertFalse(result["toolsExecuted"])
            with self.assertRaises(IntegrationError): planner.plan("hello",model="model-b")

    def test_invalid_model_does_not_send_request(self):
        with patch("qmoosa_runtime.ai.build_opener") as opener:
            with self.assertRaises(ValueError): self.planner(enabled=True).plan("hello",model="../evil")
            opener.assert_not_called()

    def test_function_calls_and_incomplete_ai_answers_rejected(self):
        for candidate in [{"finishReason":"STOP","content":{"parts":[{"functionCall":{"name":"send_funds"}}]}},{"finishReason":"MAX_TOKENS","content":{"parts":[{"text":"partial"}]}}]:
            with patch("qmoosa_runtime.ai.build_opener") as opener:
                opener.return_value.open.return_value=io.BytesIO(json.dumps({"candidates":[candidate]}).encode())
                with self.assertRaises(IntegrationError): self.planner(enabled=True).plan("hi",model="model-a")

    def test_failed_ai_attempt_consumes_budget_and_redacts_exception(self):
        planner=self.planner(enabled=True)
        with patch("qmoosa_runtime.ai.build_opener",side_effect=OSError("secret-url-token")):
            with self.assertRaises(IntegrationError) as caught: planner.plan("hello",model="model-a")
        self.assertNotIn("secret-url-token",str(caught.exception))
        with self.assertRaisesRegex(IntegrationError,"BUDGET"): planner.plan("hello",model="model-a")

    def reader(self): return EvmReader("https://example.invalid",11155111)

    def event(self, **change):
        item=dict(address=ADDRESS,removed=False,blockNumber="0xa",blockHash=HASH,transactionHash=OTHER,logIndex="0x0",topics=[OTHER],data="0x")
        return dict(item,**change)

    def test_quantities_and_arbitrum_are_rejected(self):
        for value in [True,1,"0x01","-1","0x"]:
            with self.assertRaises(ValueError): quantity(value)
        for chain in [42161,42170,421614]:
            with self.assertRaises(ValueError): EvmReader("https://example.invalid",chain)

    def test_rpc_blocks_signing(self):
        with self.assertRaises(ValueError): self.reader().rpc("eth_sendTransaction",[])

    def test_sync_returns_validated_events_and_checkpoint(self):
        reader=self.reader()
        values=["0xaa36a7","0x15",{"number":"0xa","hash":HASH},[self.event()],{"number":"0xa","hash":HASH}]
        with patch.object(reader,"rpc",side_effect=values):
            page=reader.sync_page(address=ADDRESS,start=10)
        self.assertEqual(page["checkpoint"]["blockNumber"],10)
        self.assertEqual(len(page["events"]),1)
        self.assertIn("11155111:",page["events"][0]["eventId"])
        self.assertEqual(page["status"],"PROVIDER_OBSERVED_NOT_FINALIZED")

    def test_wrong_chain_reorg_and_checkpoint_identity_block_sync(self):
        reader=self.reader()
        with patch.object(reader,"rpc",return_value="0x1"):
            with self.assertRaisesRegex(ValueError,"Wrong chain"): reader.sync_page(address=ADDRESS,start=10)
        cp=dict(chainId=11155111,address=ADDRESS,blockNumber=9,blockHash=HASH)
        with patch.object(reader,"rpc",side_effect=["0xaa36a7",{"number":"0x9","hash":OTHER}]):
            with self.assertRaisesRegex(ValueError,"REORG"): reader.sync_page(address=ADDRESS,start=10,checkpoint=cp)
        with patch.object(reader,"rpc",return_value="0xaa36a7"):
            with self.assertRaisesRegex(ValueError,"identity"): reader.sync_page(address=ADDRESS,start=10,checkpoint=dict(cp,address="other"))

    def test_removed_unrelated_duplicate_and_noncanonical_events_rejected(self):
        reader=self.reader()
        for events in [[self.event(removed=True)],[self.event(address="0x"+"44"*20)],[self.event(),self.event()],[self.event(blockHash=OTHER)]]:
            with patch.object(reader,"rpc",side_effect=["0xaa36a7","0x15",{"number":"0xa","hash":HASH},events]):
                with self.assertRaises(ValueError): reader.sync_page(address=ADDRESS,start=10)

    def test_reorg_during_sync_rejected(self):
        reader=self.reader()
        with patch.object(reader,"rpc",side_effect=["0xaa36a7","0x15",{"number":"0xa","hash":HASH},[],{"number":"0xa","hash":OTHER}]):
            with self.assertRaisesRegex(ValueError,"REORG_DURING"): reader.sync_page(address=ADDRESS,start=10)

    def test_head_without_enough_confirmations_waits(self):
        reader=self.reader()
        with patch.object(reader,"rpc",side_effect=["0xaa36a7","0xa"]):
            self.assertEqual(reader.sync_page(address=ADDRESS,start=10)["status"],"WAITING_FOR_CONFIRMATIONS")

    def test_full_qubo_objective_known_optimum_and_bounds(self):
        result=solve_qubo([[-1,2],[2,-2]])
        self.assertEqual(result["state"],[0,1])
        self.assertEqual(result["energy"],-2)
        self.assertFalse(result["quantumHardwareUsed"])
        for matrix in [[],[[float("nan")]],[[True]],[[0]*13]*13,[[1,2]]]:
            with self.assertRaises(ValueError): solve_qubo(matrix)

if __name__=="__main__": unittest.main()
