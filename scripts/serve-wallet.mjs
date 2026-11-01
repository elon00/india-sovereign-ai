import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const files = new Map([['/', ['index.html', 'text/html']], ['/app.mjs', ['app.mjs', 'text/javascript']], ['/transfer.mjs', ['transfer.mjs', 'text/javascript']]]);
export function createWalletServer() {
  return createServer(async (req, res) => {
    const entry = files.get(req.url);
    if (req.method !== 'GET' || !entry) { res.writeHead(404); res.end(); return; }
    try {
      const body = await readFile(new URL('../web/' + entry[0], import.meta.url));
      res.writeHead(200, { 'Content-Type': entry[1] + '; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'" }); res.end(body);
    } catch { res.writeHead(500); res.end('Local application unavailable'); }
  });
}
if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  createWalletServer().listen(4173, '127.0.0.1', () => console.log('Wallet prototype: http://127.0.0.1:4173 (Sepolia only)'));
}
