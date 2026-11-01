import { TokenTransfer } from './transfer.mjs';
const byId = id => document.getElementById(id);
let flow, observation;
const show = value => { byId('status').textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); };
function client() {
  if (!flow) {
    flow = new TokenTransfer(window.ethereum);
    for (const event of ['accountsChanged', 'chainChanged', 'disconnect']) window.ethereum.on(event, () => {
      byId('account').textContent = 'Wallet changed; reconnect before sending';
      byId('reviewed').checked = false;
      show('Wallet changed. Reconnect and review the transfer again. Existing submissions can still be checked on Sepolia.');
    });
  }
  return flow;
}
async function action(work) {
  const buttons = [...document.querySelectorAll('button')]; buttons.forEach(b => b.disabled = true);
  try { await work(); } catch (error) { show(error.code === 4001 ? 'Wallet request rejected. No success is claimed.' : String(error.message ?? 'Wallet operation failed.').slice(0, 400)); }
  finally { buttons.forEach(b => b.disabled = false); byId('download').disabled = !observation; byId('account').textContent = flow?.account ?? 'No account connected; reconnect after wallet changes'; }
}
byId('connect').onclick = () => action(async () => { await client().connect(); show('Connected on Sepolia. Enter and review the transfer details.'); });
byId('switch').onclick = () => action(async () => { await client().switchNetwork(); show('Network switched. Connect again before sending.'); });
byId('form').onsubmit = event => { event.preventDefault(); action(async () => {
  observation = null;
  const hash = await client().send({ token: byId('token').value.trim(), recipient: byId('recipient').value.trim(), amount: byId('amount').value.trim(), reviewed: byId('reviewed').checked });
  byId('reviewed').checked = false; byId('explorer').href = 'https://sepolia.etherscan.io/tx/' + hash; byId('explorer').hidden = false;
  show({ status: 'SUBMITTED_NOT_CONFIRMED', hash });
}); };
byId('observe').onclick = () => action(async () => { observation = { ...await client().observe(), observedAt: new Date().toISOString(), evidenceKind: 'wallet-provider-observation', limitation: 'Provider-reported data; not independent attestation, source verification or product certification' }; show(observation); });
byId('download').onclick = () => { if (!observation) return; const url = URL.createObjectURL(new Blob([JSON.stringify(observation, null, 2)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = 'sepolia-transfer-observation.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
window.addEventListener('beforeunload', () => flow?.dispose());
