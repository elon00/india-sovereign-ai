import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from qmoosa_runtime.chain import EvmReader
class TransportTests(unittest.TestCase):
    def test_real_http_transport_and_event_checkpoint(self):
        seen=[]; block_hash="0x"+"22"*32
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                packet=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append(packet["method"])
                values={"eth_chainId":"0xaa36a7","eth_blockNumber":"0x15","eth_getBlockByNumber":{"number":"0xa","hash":block_hash},"eth_getLogs":[]}
                body=json.dumps({"jsonrpc":"2.0","id":packet["id"],"result":values[packet["method"]]}).encode()
                self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            page=EvmReader("http://127.0.0.1:"+str(server.server_port),11155111).sync_page(address="0x"+"11"*20,start=10)
            self.assertEqual(page["checkpoint"]["blockHash"],block_hash)
            self.assertEqual(seen,["eth_chainId","eth_blockNumber","eth_getBlockByNumber","eth_getLogs","eth_getBlockByNumber"])
        finally: server.shutdown();server.server_close();thread.join(timeout=2)
if __name__=="__main__": unittest.main()
