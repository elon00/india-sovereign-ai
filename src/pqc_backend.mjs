// Local stdio bridge only. Secret material is transported to the Python caller,
// never put in argv, log messages, files or a network service.
import { ml_kem768 } from '@noble/post-quantum/ml-kem.js';
import { ml_dsa65 } from '@noble/post-quantum/ml-dsa.js';

const hex = (value, length) => {
  if (typeof value !== 'string' || value.length !== length * 2 || !/^[0-9a-f]+$/i.test(value)) throw new Error('Invalid field');
  return Uint8Array.from(Buffer.from(value, 'hex'));
};
const message = value => {
  if (typeof value !== 'string' || value.length > 32768 || value.length % 2 || !/^[0-9a-f]*$/i.test(value)) throw new Error('Invalid message');
  return Uint8Array.from(Buffer.from(value, 'hex'));
};
const encode = value => Buffer.from(value).toString('hex');

function dispatch(request) {
  if (!request || Array.isArray(request) || typeof request !== 'object') throw new Error('Invalid request');
  switch (request.operation) {
    case 'keygen': {
      const kem = ml_kem768.keygen();
      const dsa = ml_dsa65.keygen();
      return { kemPublic: encode(kem.publicKey), kemSecret: encode(kem.secretKey), dsaPublic: encode(dsa.publicKey), dsaSecret: encode(dsa.secretKey) };
    }
    case 'encapsulate': {
      const result = ml_kem768.encapsulate(hex(request.publicKey, 1184));
      return { cipherText: encode(result.cipherText), sharedSecret: encode(result.sharedSecret) };
    }
    case 'decapsulate':
      return { sharedSecret: encode(ml_kem768.decapsulate(hex(request.cipherText, 1088), hex(request.secretKey, 2400))) };
    case 'sign':
      return { signature: encode(ml_dsa65.sign(message(request.message), hex(request.secretKey, 4032))) };
    case 'verify':
      return { valid: ml_dsa65.verify(hex(request.signature, 3309), message(request.message), hex(request.publicKey, 1952)) };
    default:
      throw new Error('Unsupported operation');
  }
}

try {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > 131072) throw new Error('Request too large');
    chunks.push(chunk);
  }
  const result = dispatch(JSON.parse(Buffer.concat(chunks).toString('utf8')));
  process.stdout.write(JSON.stringify(result));
} catch {
  // Do not include request bodies, keys, library errors or stack traces.
  process.stderr.write('PQC backend rejected the request or is unavailable.\n');
  process.exitCode = 1;
}
