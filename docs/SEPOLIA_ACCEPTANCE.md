# India pilot: wallet-connected test-token transfer

Accepted workflow: the owner selected wallet-connected token transfer on a testnet. Proposed initial chain: Ethereum Sepolia (11155111 / 0xaa36a7), the Ethereum documentation's default application testnet. This is a cryptocurrency prototype with no government affiliation. No token mint, contract deployment or mainnet action is part of this change.

## Start

1. Install Node 22+, Python 3.10+ and a browser wallet supporting EIP-1193.
2. In this repository run `npm ci --ignore-scripts`, then `npm test`.
3. Run `npm run start:wallet`; open http://127.0.0.1:4173 in the wallet-enabled browser. The server binds only to the local computer and serves three public application assets.
4. Obtain test ETH and an independently verified standard ERC-20 test token on Sepolia. Check the contract and recipient carefully. This prototype accepts verified lowercase addresses and tokens with decimals() and transfer() returning true. Nonstandard, fee-on-transfer and malicious contracts are outside this acceptance scope.
5. Switch to Sepolia, connect, enter the token address, recipient and amount, then explicitly acknowledge the review checkbox. Check the wallet's network, token contract, recipient and amount again before approving. Reject any unexpected operation. The app never requests token allowance or a private key.
6. Save the transaction hash. Keep this tab open; pending state is memory-only. If a request times out or the outcome is uncertain, inspect wallet activity before retrying or reloading. Unknown submissions block repeat requests within the session.
7. Click Check transaction. Pending and reverted transactions cannot pass. Confirmation requires the expected transaction and exact token/from/to/amount Transfer event in a canonical receipt block. Twelve confirmations are reported as confirmed, explicitly not finalized. Download the observation and independently inspect the Sepolia explorer.

## Automated acceptance

`npm run test:wallet` exercises exact amounts and overflow, wrong-chain blocking, wallet account/network invalidation, empty token code, insufficient balance, false-returning tokens, invalid gas response, wallet rejection, uncertain-outcome duplicate blocking, calldata, pending/reverted receipts, wrong/missing events, reorgs, listener cleanup and local-server exposure. The provider is simulated in these tests. These tests are not live blockchain evidence.

## Live acceptance still required

- Record the reviewed source commit and build identity; independently verify the actual token's deployed source and network.
- Connect an owner-controlled test wallet and transfer a small amount of test tokens to an owner-controlled recipient. No funded key should be supplied to the agent.
- Independently check sender/recipient balances, transaction input, receipt, event amount and confirmation history on Sepolia.
- Reject an intentional wallet request and test a wrong-network attempt without broadcasting there.
- Keep genuine observation JSON, transaction/explorer reference, exact source and test timestamps together. Provider observations are not signed attestations.
- Production custody, independent RPC corroboration, persistent recovery across browser restarts, broader wallet compatibility, finalized-block proof, external security review and real user acceptance remain open gates.

No live transfer or deployment is claimed by local tests. The app cannot infer contract trustworthiness from bytecode presence or an event. Sepolia tokens have no production utility in this pilot. Keep all production/mainnet spending disabled until the full applicable release gates and concrete owner approval.

References: https://ethereum.org/developers/docs/networks/ ; https://eips.ethereum.org/EIPS/eip-1193 ; https://eips.ethereum.org/EIPS/eip-20 .
