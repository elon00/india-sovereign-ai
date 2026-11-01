import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { TokenTransfer, CHAIN, units } from '../web/transfer.mjs';
import { createWalletServer } from '../scripts/serve-wallet.mjs';
const sender = '0x' + '11'.repeat(20), token = '0x' + '22'.repeat(20), recipient = '0x' + '33'.repeat(20);
const hash = '0x' + '44'.repeat(32), blockHash = '0x' + '55'.repeat(32);
const hex = x => '0x' + BigInt(x).toString(16).padStart(64, '0');
const topic = x => '0x' + x.slice(2).padStart(64, '0');
const request = { token, recipient, amount: '1.25', reviewed: true };
function fixture() {
  const listeners = new Map(), calls = [];
  const state = { chain: CHAIN, accounts: [sender], balance: 2000000n, result: 1, code: '0x6000', outcome: 'ok', receipt: undefined, gas: '0x8000', blockHash };
  const provider = { on(e, f) { listeners.set(e, f); }, removeListener(e) { listeners.delete(e); }, async request({ method, params }) {
    calls.push({ method, params });
    switch (method) {
      case 'eth_chainId': return state.chain;
      case 'eth_accounts': case 'eth_requestAccounts': return state.accounts;
      case 'wallet_switchEthereumChain': state.chain = params[0].chainId; listeners.get('chainChanged')?.(); return null;
      case 'eth_getCode': return state.code;
      case 'eth_call': return params[0].data === '0x313ce567' ? hex(6) : params[0].data.startsWith('0x70a08231') ? hex(state.balance) : hex(state.result);
      case 'eth_estimateGas': return state.gas;
      case 'eth_sendTransaction':
        if (state.outcome === 'rejected') throw Object.assign(Error('Rejected'), { code: 4001 });
        if (state.outcome === 'timeout') throw Error('Unknown submission outcome');
        return hash;
      case 'eth_getTransactionReceipt': return state.receipt ?? null;
      case 'eth_getTransactionByHash': { const tx = calls.find(c => c.method === 'eth_sendTransaction').params[0]; return { ...tx, input: tx.data }; }
      case 'eth_getBlockByNumber': return { hash: state.blockHash };
      case 'eth_blockNumber': return '0x20';
      default: throw Error('Unexpected RPC method ' + method);
    }
  } };
  const flow = new TokenTransfer(provider);
  function mined() { state.receipt = { transactionHash: hash, from: sender, to: token, status: '0x1', blockHash, blockNumber: '0x10', logs: [{ address: token, topics: ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef', topic(sender), topic(recipient)], data: hex(1250000) }] }; }
  return { flow, state, calls, listeners, mined };
}
test('amount conversion is exact and rejects rounding, zero and overflow', () => {
  assert.equal(units('1.000001', 6), 1000001n);
  for (const value of ['0', '-1', '1e3', '01', '1.0000001', 'NaN', '9'.repeat(90)]) assert.throws(() => units(value, 6));
});
test('wrong chain and absent account cannot request a transfer', async () => {
  const x = fixture(); x.state.chain = '0x1'; await assert.rejects(x.flow.connect(), /Sepolia only/);
  await assert.rejects(x.flow.send(request)); assert.equal(x.calls.some(c => c.method === 'eth_sendTransaction'), false);
});
test('review, contract code, balance and false-returning token fail before wallet signing', async () => {
  for (const mutation of [x => { x.reviewed = false; }, () => {}]) {
    const x = fixture(); await x.flow.connect(); const r = { ...request }; mutation(r);
    if (r.reviewed) x.state.balance = 0n;
    await assert.rejects(x.flow.send(r)); assert.equal(x.calls.some(c => c.method === 'eth_sendTransaction'), false);
  }
  for (const [field, value] of [['result', 0], ['code', '0x'], ['gas', 100]]) {
    const x = fixture(); await x.flow.connect(); x.state[field] = value;
    await assert.rejects(x.flow.send(request)); assert.equal(x.calls.some(c => c.method === 'eth_sendTransaction'), false);
  }
});
test('account and network events invalidate authorization', async () => {
  for (const event of ['accountsChanged', 'chainChanged', 'disconnect']) {
    const x = fixture(); await x.flow.connect(); x.listeners.get(event)();
    await assert.rejects(x.flow.send(request), /Wallet changed/); assert.equal(x.calls.some(c => c.method === 'eth_sendTransaction'), false);
  }
});
test('the normal accountsChanged event during initial permission does not break connection', async () => {
  const x = fixture();
  const original = x.flow.provider.request.bind(x.flow.provider);
  x.flow.provider.request = async arg => {
    const result = await original(arg);
    if (arg.method === 'eth_requestAccounts') x.listeners.get('accountsChanged')();
    return result;
  };
  assert.equal(await x.flow.connect(), sender);
});
test('wallet rejection permits explicit retry; ambiguous submission blocks duplicates', async () => {
  const x = fixture(); await x.flow.connect(); x.state.outcome = 'rejected'; await assert.rejects(x.flow.send(request)); assert.equal(x.flow.pending, null);
  x.state.outcome = 'timeout'; await assert.rejects(x.flow.send(request));
  await assert.rejects(x.flow.send(request), /already in progress/);
  assert.equal(x.calls.filter(c => c.method === 'eth_sendTransaction').length, 2);
});
test('ERC20 submission uses exact amount, zero native value and explicit Sepolia chain', async () => {
  const x = fixture(); await x.flow.connect(); assert.equal(await x.flow.send(request), hash);
  const tx = x.calls.find(c => c.method === 'eth_sendTransaction').params[0];
  assert.deepEqual(tx, { from: sender, to: token, value: '0x0', data: '0xa9059cbb' + recipient.slice(2).padStart(64, '0') + hex(1250000).slice(2), chainId: CHAIN });
  assert.equal((await x.flow.observe()).status, 'PENDING');
  await assert.rejects(x.flow.send(request), /already in progress/);
});
test('matching receipt and event yield confirmations without claiming finality', async () => {
  const x = fixture(); await x.flow.connect(); await x.flow.send(request); x.mined();
  const result = await x.flow.observe(); assert.equal(result.status, 'CONFIRMED_NOT_FINALIZED'); assert.equal(result.confirmations, '17'); assert.equal(result.finalized, false); assert.equal(result.sourceMatch, 'NOT_ESTABLISHED');
});
test('reverted, missing event, wrong event value, mismatched receipt and reorg cannot confirm', async () => {
  const cases = [x => { x.state.receipt.logs = []; }, x => { x.state.receipt.logs[0].data = hex(1); }, x => { x.state.receipt.to = sender; }, x => { x.state.blockHash = '0x' + '66'.repeat(32); }];
  for (const mutate of cases) { const x = fixture(); await x.flow.connect(); await x.flow.send(request); x.mined(); mutate(x); await assert.rejects(x.flow.observe()); }
  const x = fixture(); await x.flow.connect(); await x.flow.send(request); x.mined(); x.state.receipt.status = '0x0'; assert.equal((await x.flow.observe()).status, 'REVERTED');
});
test('switching network never signs, and disposal removes provider listeners', async () => {
  const x = fixture(); await x.flow.switchNetwork(); assert.equal(x.calls.some(c => c.method === 'eth_sendTransaction'), false); x.flow.dispose(); assert.equal(x.listeners.size, 0);
});
test('local server serves only public app assets and excludes source, secrets and POST', async () => {
  const server = createWalletServer(); server.listen(0, '127.0.0.1'); await once(server, 'listening');
  try {
    const base = 'http://127.0.0.1:' + server.address().port;
    const page = await fetch(base); assert.equal(page.status, 200); assert.match(await page.text(), /Sepolia/); assert.match(page.headers.get('content-security-policy'), /frame-ancestors 'none'/);
    for (const path of ['/app.mjs', '/transfer.mjs']) assert.equal((await fetch(base + path)).status, 200);
    for (const path of ['/.env', '/src/pqc_layer.py', '/package.json', '/../package.json']) assert.equal((await fetch(base + path)).status, 404);
    assert.equal((await fetch(base, { method: 'POST' })).status, 404);
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});
