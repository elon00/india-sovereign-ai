// Sepolia-only ERC-20 transfer. No private keys, approvals, custom RPC URLs or mainnet path.
export const CHAIN = '0xaa36a7';
const TRANSFER_EVENT = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef';
const UINT_MAX = (1n << 256n) - 1n;
export function address(value) {
  if (typeof value !== 'string' || !/^0x[0-9a-f]{40}$/i.test(value) || /^0x0{40}$/i.test(value)) throw Error('Enter a nonzero 20-byte address.');
  // Mixed-case checksums need a dedicated checksum validator. Do not silently accept a typo.
  if (value !== value.toLowerCase()) throw Error('Use a verified lowercase address for this prototype.');
  return value;
}
const word = value => value.toString(16).padStart(64, '0');
const addressWord = value => address(value).slice(2).padStart(64, '0');
function uint(value) {
  if (typeof value !== 'string' || !/^0x[0-9a-f]{64}$/i.test(value)) throw Error('Malformed token response.');
  return BigInt(value);
}
export function units(value, decimals) {
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 36 || typeof value !== 'string' || value.length > 100 || !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value)) throw Error('Invalid amount or unsupported decimals.');
  const [whole, fraction = ''] = value.split('.');
  if (fraction.length > decimals) throw Error('Amount exceeds token precision.');
  const result = BigInt(whole) * 10n ** BigInt(decimals) + BigInt(fraction.padEnd(decimals, '0') || '0');
  if (result <= 0n || result > UINT_MAX) throw Error('Amount must be positive and fit uint256.');
  return result;
}
export class TokenTransfer {
  constructor(provider) {
    if (!provider?.request || !provider?.on || !provider?.removeListener) throw Error('Install an EIP-1193 browser wallet.');
    this.provider = provider; this.generation = 0; this.pending = null; this.busy = false;
    this.invalidate = () => { this.generation++; this.account = null; };
    for (const event of ['accountsChanged', 'chainChanged', 'disconnect']) provider.on(event, this.invalidate);
  }
  dispose() { for (const event of ['accountsChanged', 'chainChanged', 'disconnect']) this.provider.removeListener(event, this.invalidate); this.invalidate(); }
  rpc(method, params = []) { return this.provider.request({ method, params }); }
  async assertSession(generation = this.generation) {
    if (await this.rpc('eth_chainId') !== CHAIN) throw Error('Sepolia only. Switch your wallet network.');
    const accounts = await this.rpc('eth_accounts');
    if (generation !== this.generation || !this.account || !Array.isArray(accounts) || accounts[0]?.toLowerCase() !== this.account) throw Error('Wallet changed. Reconnect and review again.');
  }
  async connect() {
    this.invalidate();
    const accounts = await this.rpc('eth_requestAccounts');
    if (!Array.isArray(accounts) || !accounts.length) throw Error('No wallet account available.');
    this.account = address(accounts[0].toLowerCase());
    await this.assertSession(this.generation); return this.account;
  }
  async switchNetwork() { this.invalidate(); await this.rpc('wallet_switchEthereumChain', [{ chainId: CHAIN }]); }
  async send({ token, recipient, amount, reviewed }) {
    if (this.busy || this.pending) throw Error('A transfer is already in progress. Check its status first.');
    if (reviewed !== true) throw Error('Review the testnet transfer before requesting wallet approval.');
    token = address(token); recipient = address(recipient);
    const generation = this.generation;
    this.busy = true;
    try {
      await this.assertSession(generation);
      const code = await this.rpc('eth_getCode', [token, 'latest']);
      if (typeof code !== 'string' || !/^0x(?:[0-9a-f]{2})+$/i.test(code) || /^0x0+$/i.test(code)) throw Error('No token contract code at this address.');
      const call = data => this.rpc('eth_call', [{ to: token, from: this.account, data }, 'latest']);
      const decimals = Number(uint(await call('0x313ce567')));
      const value = units(amount, decimals);
      const balance = uint(await call('0x70a08231' + addressWord(this.account)));
      if (balance < value) throw Error('Insufficient test-token balance.');
      const tx = { from: this.account, to: token, value: '0x0', data: '0xa9059cbb' + addressWord(recipient) + word(value), chainId: CHAIN };
      // A successful eth_call returning false is not a successful ERC-20 transfer.
      if (uint(await call(tx.data)) !== 1n) throw Error('Token transfer simulation did not return true.');
      const gas = await this.rpc('eth_estimateGas', [tx]);
      if (typeof gas !== 'string' || !/^0x[1-9a-f][0-9a-f]*$/i.test(gas)) throw Error('Invalid gas estimate.');
      await this.assertSession(generation);
      // The provider is untrusted. The wallet must independently show the intended chain and action.
      this.pending = { status: 'UNKNOWN_SUBMISSION', token, recipient, value: value.toString(), tx };
      let hash;
      try { hash = await this.rpc('eth_sendTransaction', [tx]); }
      catch (error) {
        if (error?.code === 4001) this.pending = null;
        throw error;
      }
      if (typeof hash !== 'string' || !/^0x[0-9a-f]{64}$/i.test(hash)) {
        this.pending = { status: 'UNKNOWN_SUBMISSION', token, recipient, value: value.toString(), tx };
        throw Error('Submission response is unknown. Inspect wallet activity before retrying.');
      }
      this.pending = { hash, token, recipient, value: value.toString(), tx };
      return hash;
    } finally { this.busy = false; }
  }
  async observe() {
    const p = this.pending;
    if (!p?.hash) throw Error('No known transaction hash. Inspect wallet activity if submission was uncertain.');
    if (await this.rpc('eth_chainId') !== CHAIN) throw Error('Return to Sepolia to observe this transfer.');
    const receipt = await this.rpc('eth_getTransactionReceipt', [p.hash]);
    if (!receipt) return { status: 'PENDING', hash: p.hash };
    if (receipt.transactionHash?.toLowerCase() !== p.hash.toLowerCase() || receipt.to?.toLowerCase() !== p.token || receipt.from?.toLowerCase() !== p.tx.from) throw Error('Receipt does not match the requested transfer.');
    if (receipt.status === '0x0') return { status: 'REVERTED', hash: p.hash };
    if (receipt.status !== '0x1' || typeof receipt.blockHash !== 'string' || !/^0x[0-9a-f]{64}$/i.test(receipt.blockHash) || typeof receipt.blockNumber !== 'string' || !/^0x(?:0|[1-9a-f][0-9a-f]*)$/i.test(receipt.blockNumber)) throw Error('Malformed receipt.');
    const tx = await this.rpc('eth_getTransactionByHash', [p.hash]);
    if (!tx || tx.to?.toLowerCase() !== p.token || tx.from?.toLowerCase() !== p.tx.from || tx.input?.toLowerCase() !== p.tx.data || tx.value !== '0x0') throw Error('Observed transaction differs from the approved action.');
    const matchingEvent = Array.isArray(receipt.logs) && receipt.logs.some(log => !log.removed && log.address?.toLowerCase() === p.token && log.topics?.length === 3 && log.topics[0]?.toLowerCase() === TRANSFER_EVENT && log.topics[1]?.toLowerCase() === '0x' + addressWord(p.tx.from) && log.topics[2]?.toLowerCase() === '0x' + addressWord(p.recipient) && log.data?.toLowerCase() === '0x' + word(BigInt(p.value)));
    if (!matchingEvent) throw Error('Expected ERC-20 Transfer event missing.');
    const block = await this.rpc('eth_getBlockByNumber', [receipt.blockNumber, false]);
    if (block?.hash?.toLowerCase() !== receipt.blockHash.toLowerCase()) throw Error('Receipt block was reorganized. Recheck later.');
    const head = await this.rpc('eth_blockNumber');
    if (typeof head !== 'string' || !/^0x(?:0|[1-9a-f][0-9a-f]*)$/i.test(head) || BigInt(head) < BigInt(receipt.blockNumber)) throw Error('Invalid current block.');
    const confirmations = BigInt(head) - BigInt(receipt.blockNumber) + 1n;
    if (await this.rpc('eth_chainId') !== CHAIN) throw Error('Network changed during verification.');
    return { status: confirmations >= 12n ? 'CONFIRMED_NOT_FINALIZED' : 'CONFIRMING', hash: p.hash, confirmations: confirmations.toString(), blockHash: receipt.blockHash, chainId: CHAIN, token: p.token, recipient: p.recipient, amountBaseUnits: p.value, finalized: false, sourceMatch: 'NOT_ESTABLISHED' };
  }
}
