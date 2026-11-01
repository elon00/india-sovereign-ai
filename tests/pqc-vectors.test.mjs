// These are published public NIST test keys, never live or application keys.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ml_kem768 } from '@noble/post-quantum/ml-kem.js';
import { ml_dsa65 } from '@noble/post-quantum/ml-dsa.js';

const fixture = JSON.parse(readFileSync(new URL('./vectors/nist-keygen.json', import.meta.url), 'utf8'));
assert.equal(fixture.vectors.length, 2);
for (const vector of fixture.vectors) {
  test(`${vector.algorithm}: published NIST ACVP keygen group ${vector.tgId}, case ${vector.tcId}`, () => {
    const kem = vector.algorithm === 'ML-KEM-768';
    assert.ok(kem || vector.algorithm === 'ML-DSA-65');
    const seed = Buffer.from(kem ? vector.input.d + vector.input.z : vector.input.seed, 'hex');
    const generated = kem ? ml_kem768.keygen(seed) : ml_dsa65.keygen(seed);
    const expectedPublic = Buffer.from(kem ? vector.expected.ek : vector.expected.pk, 'hex');
    const expectedSecret = Buffer.from(kem ? vector.expected.dk : vector.expected.sk, 'hex');
    assert.equal(Buffer.compare(Buffer.from(generated.publicKey), expectedPublic), 0, 'Public key must match the independent NIST vector');
    assert.equal(Buffer.compare(Buffer.from(generated.secretKey), expectedSecret), 0, 'Public test secret key must match the independent NIST vector');
  });
}
