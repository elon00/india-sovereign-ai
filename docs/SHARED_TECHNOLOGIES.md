# Shared technology integration, version 0.1.0

QARBI is a read-only architecture reference; no QARBI code, defaults, Arbitrum network or dependencies are modified. Reuse existing domain modules; do not replace the project with a generic template. These modules are additive and have no third-party Python dependencies.

## Implemented local components

`qmoosa_runtime.ai.GeminiPlanner`: Gemini REST text planning with configured model allowlist, opt-in request, one-attempt default, bounded inputs/outputs, redirect rejection and no tool execution. Requests may incur provider costs only when explicitly invoked. Request caps are per client/process, not monetary or distributed rate limits. No AI credential has been used in verification. This is not a chatbot authentication service or complete autonomous agent.

`qmoosa_runtime.chain.EvmReader`: read-only EVM event paging, chain checks, bounded block/log responses, canonical hash validation, checkpoints bound to chain/address, event deduplication and reorganization detection. The consumer must store events and returned checkpoint together in its database transaction, and handle rollback/replay on a reorganization. This library does not certify economic finality, independent-provider agreement, proof verification or durable recovery. RPC URLs are server-side settings supplied by the operator; do not accept untrusted user-provided endpoints.

`qmoosa_runtime.quantum.solve_qubo`: exact classical exhaustive reference for 1â€“12 binary variables, using the full x^T Q x objective. This is a useful small-instance correctness baseline, not quantum hardware, quantum advantage or financial advice.

`qmoosa_runtime.deployment.prepare_sepolia_creation`: unsigned, zero-native-value Sepolia creation transaction preparation from caller-supplied compiled init bytecode and source digest. No signing, broadcasting, gas estimation, source/bytecode matching or deployment. A source digest supplied by a caller is not source-match evidence.

## Run from the repository root

    python -B -m unittest discover -s tests -p "test_shared_*.py" -v
    python -B -m qmoosa_runtime --help
    python -B -m qmoosa_runtime qubo --matrix-file matrix.json

For the QUBO example, matrix.json can contain `[[-1,2],[2,-2]]`.
AI calls require GEMINI_API_KEY in the server environment, an explicit --model, --prompt-file and --allow-provider-request. Never put personal health, legal, identity or confidential records into a provider request without the application's appropriate data controls. Prompts are untrusted and outputs are advisory; application-level auth, privacy review, model evaluation and tool authorization remain required.

Read-only sync requires QUICKNODE_RPC_URL in the server environment and explicit --chain-id, --address and --start. Example Sepolia:

    python -B -m qmoosa_runtime sync --chain-id 11155111 --address 0x1c7d4b196cb0c7b01d743fbc6116a902379c7238 --start BLOCK_NUMBER

Replace BLOCK_NUMBER with a recent integer. The current adapter blocks Arbitrum One, Nova and Sepolia IDs; any additional chain adapter still requires ancestry/compatibility review. It does not make every EVM or native chain supported. Existing ICP or other native project architecture is preserved; optional EVM research is not a primary-chain migration. For ICP, native canister integration and cycles remain separate, unverified work.

For unsigned creation preparation, artifact JSON must contain sender, init_bytecode, source_sha256 and gas_limit. Run `python -B -m qmoosa_runtime prepare-deployment --artifact-file artifact.json`. Use only genuinely compiled artifacts. Review source, bytecode, network, constructor and wallet details before any manual wallet submission. No contract artifact or transaction is fabricated by this command.

## Remaining capability work

Existing Conway, PQC, wallet and payment modules remain their existing status. Presence of this package does not integrate x402 settlement/Bazaar, QuickNode Streams, Raven/REA, launchpad, QR wallets, hosted chatbot sessions, native-chain deployments or production monitoring. Every capability needs domain-specific wiring and acceptance evidence; unsupported features stay blocked. No token supply policy is silently changed.

## Sources

- QARBI architecture reference: https://github.com/elon00/QARBI/commit/bbedd84d8b041f09617d118a5b8b8e65a7a4e1bb
- Gemini API: https://ai.google.dev/api/generate-content
- Ethereum JSON-RPC: https://ethereum.org/developers/docs/apis/json-rpc/
