# India Cryptocurrency Token Project

Independent India-themed cryptocurrency/token and blockchain application prototype, maintained by elon00.

## Project identity

This project targets tokens on existing blockchain networks. The repository name is a historical identifier; asset definitions, supported chains and deployed addresses must be established from the actual implementation and verified release records.

| Item | Status |
|---|---|
| Product stage | Prototype; production readiness requires evidence |
| Asset type | Blockchain token; chain-specific standard to be selected |
| Token name, symbol and decimals | Pending project specification |
| Initial supply and emission policy | Pending tokenomics review |
| Mint, upgrade and treasury authorities | Pending role and custody design |
| Canonical chain and network identifier | Pending compatibility review |
| Testnet contract/program/asset identifier | Pending verified release evidence |
| Mainnet contract/program/asset identifier | Pending approved release evidence |

## Cryptocurrency and blockchain scope

- Implement a useful token and its application on a compatible blockchain.
- Define utility, finite issuance transactions, lifetime supply policy, emission limits, vesting, governance and treasury controls.
- Use the selected chain's token standard, wallet signing flow, transaction format, fees and finality rules.
- Integrate wallet connections, balances, transaction previews and validated payment QR payloads.
- Use authenticated RPC access and chain identity checks; configure QuickNode where the selected network supports it.
- Add x402 paid API access and Bazaar discovery only when the product has a real paid resource and supported settlement path.

EVM contracts, Solana programs, Move modules, Algorand assets, TON contracts and ICP canisters require appropriate implementations and verification. A TVL ranking does not establish cross-chain compatibility.

## Implementation and verification

Existing research or simulation modules must be evaluated separately from working token contracts, cryptographic verification and confirmed payments. A local hash, a formatted proof string, a module name or a passing CI badge does not establish those capabilities.

Before a release, record:

1. The exact source commit and reproducible build artifact.
2. Meaningful unit, regression, smoke, dependency, secret and applicable CodeQL/static-analysis results.
3. Token supply invariants, access control, unauthorized mint rejection and wallet/signature replay tests.
4. Correct chain identity, real testnet transactions, public explorer links and source-to-deployment verification.
5. Operational monitoring, recovery tests, fee budget, authorized signer and release approval.

PQC features require genuine reviewed algorithms and published-vector/negative tests. Conway B3/S23 can serve as a simulation component; its presence alone does not establish network consensus.

## Development

Requires Python 3.10+, Node.js 22+ and the locked npm dependency. Install without lifecycle scripts and run the complete component suite:

```sh
npm ci --ignore-scripts
npm test
npm audit --audit-level=high
```

Test output must describe the checks actually executed. A perfect readiness score is earned through current evidence.

## Portfolio coordination

Use [bountyhunter-os](https://github.com/elon00/bountyhunter-os) for repository-specific repair profiles, source-bound test evidence and release blocker tracking. Keep this product's source, token configuration and deployment history in this repository.

## Implemented component scope

- The existing bounded Conway simulation is retained and checked against real patterns. It is not blockchain consensus.
- Off-chain ML-KEM-768 key generation/encapsulation/decapsulation and ML-DSA-65 signing/verification use exactly @noble/post-quantum 0.7.1 through a local stdio bridge. This reuses the cryptographic implementation instead of inventing primitives.
- Two published NIST ACVP key-generation vectors are preserved with immutable upstream URLs, test IDs and full-source hashes. They validate the selected key-generation cases, not every cryptographic operation or a FIPS-validated module.
- Keys are ephemeral and memory-only. Private material travels only over captured local process pipes, never argv, logs or a network API. This is not production custody; Python/JavaScript may retain copies despite best-effort buffer clearing. Do not use this prototype for production keys or blockchain signing. Shared secrets must stay with the trusted caller; no peer authentication or key-confirmation protocol is implemented.
- Identifier methods produce local test identifiers, not government-issued DIDs, Pedersen commitments or zero-knowledge credentials. Do not use real personal identifiers.
- A formatted hash never authorizes a payment. The x402 boundary returns an unconfigured status until a genuine verification and settlement backend is integrated. Settlement execution raises instead of pretending a local hash is a ledger transaction; the separate simulation uses bounded integer base units.

The previous tests incorrectly accepted fabricated proofs and successful-looking local hashes. The replacement suite checks actual cryptographic results, tampering/wrong-key rejection, simulation bounds and fail-closed behavior. A green component suite is not an application deployment or 100/100 production/market certification. Token contracts, wallets/QR, actual x402 settlement, operational recovery and source-matched testnet workflows remain pending.
