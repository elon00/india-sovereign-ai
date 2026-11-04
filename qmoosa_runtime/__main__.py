"""Explicit CLI. AI and RPC credentials come from environment, never arguments."""
import argparse
import json
import os
from pathlib import Path
from .ai import GeminiPlanner
from .chain import EvmReader
from .quantum import solve_qubo
from .deployment import prepare_sepolia_creation

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    ai=sub.add_parser("plan"); ai.add_argument("--model",required=True); ai.add_argument("--prompt-file",required=True)
    ai.add_argument("--allow-provider-request",action="store_true")
    sync=sub.add_parser("sync"); sync.add_argument("--chain-id",type=int,required=True); sync.add_argument("--address",required=True)
    sync.add_argument("--start",type=int,required=True); sync.add_argument("--confirmations",type=int,default=12); sync.add_argument("--checkpoint-file")
    qubo=sub.add_parser("qubo"); qubo.add_argument("--matrix-file",required=True)
    deploy=sub.add_parser("prepare-deployment"); deploy.add_argument("--artifact-file",required=True)
    args=parser.parse_args()
    try:
        if args.action=="plan":
            # Disable before constructing a client so a missing key never encourages unsafe fallback.
            if not args.allow_provider_request: raise ValueError("Explicit provider request option required")
            text=Path(args.prompt_file).read_text(encoding="utf-8")
            result=GeminiPlanner(api_key=os.environ.get("GEMINI_API_KEY",""),models=[args.model],enabled=True).plan(text,model=args.model)
        elif args.action=="sync":
            checkpoint=json.loads(Path(args.checkpoint_file).read_text()) if args.checkpoint_file else None
            result=EvmReader(os.environ.get("QUICKNODE_RPC_URL",""),args.chain_id).sync_page(address=args.address,start=args.start,confirmations=args.confirmations,checkpoint=checkpoint)
        elif args.action=="qubo": result=solve_qubo(json.loads(Path(args.matrix_file).read_text()))
        else: result=prepare_sepolia_creation(**json.loads(Path(args.artifact_file).read_text()))
        print(json.dumps(result,indent=2)); return 0
    except Exception:
        # No raw provider exceptions, credentials, prompts or secret-bearing paths are printed.
        print(json.dumps({"status":"BLOCKED","reason":"Invalid input, configuration or provider response; no transaction was submitted"}));return 2

if __name__=="__main__": raise SystemExit(main())
