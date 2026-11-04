"""Read-only EVM event synchronization, bounded and pinned to canonical blocks.

Returns a proposed checkpoint; the consumer persists events and checkpoint in one
database transaction. Event IDs support idempotent replay. Confirmations are not finality.
"""
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from .ai import NoRedirect, IntegrationError


def quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)', value):
        raise ValueError('Invalid RPC quantity')
    return int(value, 16)


def fixed_hex(value, length):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{' + str(length * 2) + '}', value):
        raise ValueError('Invalid RPC data')
    return value.lower()


class EvmReader:
    METHODS = frozenset(('eth_chainId', 'eth_blockNumber', 'eth_getBlockByNumber', 'eth_getLogs', 'eth_getCode'))

    def __init__(self, endpoint, chain_id, timeout=10):
        url = urlparse(endpoint)
        if (type(chain_id) is not int or chain_id <= 0 or chain_id in (42161, 42170, 421614)
                or url.username or url.password or url.fragment
                or not (url.scheme == 'https' and url.hostname or url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost', '::1'))
                or type(timeout) not in (int, float) or not 0 < timeout <= 30):
            raise ValueError('Explicit permitted chain, secure RPC and bounded timeout required')
        self._endpoint, self.chain_id, self._timeout = endpoint, chain_id, timeout

    def rpc(self, method, params):
        if method not in self.METHODS:
            raise ValueError('Only read-only RPC methods are permitted')
        request = Request(self._endpoint, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with build_opener(NoRedirect()).open(request, timeout=self._timeout) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError('RPC response too large')
            data = json.loads(raw)
            if (not isinstance(data, dict) or data.get('jsonrpc') != '2.0'
                    or type(data.get('id')) is not int or data['id'] != 1 or 'error' in data or 'result' not in data):
                raise ValueError('Malformed RPC response')
            return data['result']
        except Exception:
            raise IntegrationError('RPC_UNAVAILABLE_OR_INVALID') from None

    def _block_hash(self, number):
        block = self.rpc('eth_getBlockByNumber', [hex(number), False])
        if not isinstance(block, dict) or quantity(block.get('number')) != number:
            raise ValueError('Unexpected block')
        return fixed_hex(block.get('hash'), 32)

    def sync_page(self, *, address, start, confirmations=12, checkpoint=None, page_size=100):
        address = fixed_hex(address, 20)
        if (address == '0x' + '00' * 20 or type(start) is not int or start < 0
                or type(confirmations) is not int or not 1 <= confirmations <= 10000
                or type(page_size) is not int or not 1 <= page_size <= 100):
            raise ValueError('Invalid synchronization limits')
        if quantity(self.rpc('eth_chainId', [])) != self.chain_id:
            raise ValueError('Wrong chain')
        if checkpoint is not None:
            if (not isinstance(checkpoint, dict) or checkpoint.get('chainId') != self.chain_id
                    or checkpoint.get('address') != address or type(checkpoint.get('blockNumber')) is not int
                    or checkpoint['blockNumber'] < 0):
                raise ValueError('Checkpoint identity mismatch')
            previous_hash = fixed_hex(checkpoint.get('blockHash'), 32)
            if self._block_hash(checkpoint['blockNumber']) != previous_hash:
                raise ValueError('REORG_REQUIRES_CONSUMER_ROLLBACK')
            start = checkpoint['blockNumber'] + 1
        latest = quantity(self.rpc('eth_blockNumber', []))
        end = min(start + page_size - 1, latest - confirmations + 1)
        if end < start:
            return {'events': [], 'checkpoint': checkpoint, 'status': 'WAITING_FOR_CONFIRMATIONS'}
        end_hash = self._block_hash(end)
        logs = self.rpc('eth_getLogs', [{'address': address, 'fromBlock': hex(start), 'toBlock': hex(end)}])
        if not isinstance(logs, list) or len(logs) > 1000:
            raise ValueError('Invalid or excessive event list')
        events, seen, block_hashes = [], set(), {end: end_hash}
        for log in logs:
            if not isinstance(log, dict) or log.get('removed') is not False or fixed_hex(log.get('address'), 20) != address:
                raise ValueError('Removed or unrelated event')
            number = quantity(log.get('blockNumber'))
            if not start <= number <= end:
                raise ValueError('Event outside requested range')
            block_hash = fixed_hex(log.get('blockHash'), 32)
            if number not in block_hashes:
                block_hashes[number] = self._block_hash(number)
            if block_hash != block_hashes[number]:
                raise ValueError('Noncanonical event')
            tx_hash, index = fixed_hex(log.get('transactionHash'), 32), quantity(log.get('logIndex'))
            topics, data = log.get('topics'), log.get('data')
            if not isinstance(topics, list) or len(topics) > 4 or any(fixed_hex(t, 32) != t.lower() for t in topics):
                raise ValueError('Invalid event topics')
            if not isinstance(data, str) or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', data):
                raise ValueError('Invalid event data')
            event_id = f'{self.chain_id}:{block_hash}:{tx_hash}:{index}'
            if event_id in seen:
                raise ValueError('Duplicate event')
            seen.add(event_id)
            events.append(dict(log, eventId=event_id))
        if self._block_hash(end) != end_hash:
            raise ValueError('REORG_DURING_SYNCHRONIZATION')
        if checkpoint is not None and self._block_hash(checkpoint['blockNumber']) != previous_hash:
            raise ValueError('REORG_DURING_SYNCHRONIZATION')
        events.sort(key=lambda e: (quantity(e['blockNumber']), quantity(e['logIndex'])))
        return {'status': 'PROVIDER_OBSERVED_NOT_FINALIZED', 'events': events,
                'checkpoint': {'chainId': self.chain_id, 'address': address, 'blockNumber': end, 'blockHash': end_hash}}
