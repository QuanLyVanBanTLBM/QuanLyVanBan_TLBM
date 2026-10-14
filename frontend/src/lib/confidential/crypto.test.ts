// @vitest-environment node
import { beforeAll, describe, expect, it } from 'vitest';
import { createIdentity, fingerprint, open, recover, seal, unlock, unb64, b64 } from './crypto';
import type { KeyRecord, UnlockedKey } from './crypto';

describe('confidential E2EE acceptance', () => {
  const password = 'long independent passphrase for tests';
  let sender: UnlockedKey, receiver: UnlockedKey, outsider: UnlockedKey;
  let recoveryCode: string;
  beforeAll(async () => {
    const identities = await Promise.all([1, 2, 3].map(id => createIdentity(id, password)));
    const unlocked = await Promise.all(identities.map((item, index) => unlock({ ...item.record, id: index + 1 }, password)));
    [sender, receiver, outsider] = unlocked;
    recoveryCode = identities[0].recoveryCode;
  }, 30000);
  const content = { number: 'SECRET-NUMBER', title: 'SECRET-TITLE', note: 'SECRET-NOTE', files: [{ name: 'SECRET-NAME.txt', data: b64(new TextEncoder().encode('secret attachment')) }] };
  const encrypted = () => seal(content, sender, [{ record: receiver.record, expected: receiver.record.fingerprint }]);
  const delivered = (doc: Awaited<ReturnType<typeof seal>>) => ({ ...doc, author_id: 1, author_fingerprint: sender.record.fingerprint });

  it('round-trips metadata and files; transport contains none of the plaintext', async () => {
    const doc = await encrypted();
    expect(JSON.stringify(doc)).not.toMatch(/SECRET-|secret attachment/);
    expect(await open(delivered(doc), receiver, sender.record, sender.record.fingerprint)).toEqual(content);
    expect(await open(delivered(doc), sender, sender.record, sender.record.fingerprint)).toEqual(content);
  });
  it('rejects a logged-in outsider with a different private key', async () => {
    const doc = delivered(await encrypted());
    await expect(open(doc, outsider, sender.record, sender.record.fingerprint)).rejects.toThrow();
    doc.envelopes[1].key_id = outsider.record.id;
    await expect(open(doc, outsider, sender.record, sender.record.fingerprint)).rejects.toThrow();
  });
  it('rejects changed ciphertext, nonce, signature, identity and envelope', async () => {
    const original = delivered(await encrypted());
    for (const field of ['ciphertext', 'nonce', 'signature'] as const) {
      const doc = structuredClone(original);
      const bytes = unb64(doc[field]); bytes[0] ^= 1; doc[field] = b64(bytes);
      await expect(open(doc, receiver, sender.record, sender.record.fingerprint)).rejects.toThrow();
    }
    await expect(open({ ...original, author_id: 3 }, receiver, sender.record, sender.record.fingerprint)).rejects.toThrow();
    const doc = structuredClone(original); doc.envelopes[0].wrapped_key = outsider.record.encryption_public_key;
    await expect(open(doc, receiver, sender.record, sender.record.fingerprint)).rejects.toThrow();
  });
  it('blocks unverified or substituted public keys before encryption', async () => {
    await expect(seal(content, sender, [{ record: receiver.record, expected: '' }])).rejects.toThrow();
    await expect(seal(content, sender, [{ record: outsider.record, expected: receiver.record.fingerprint }])).rejects.toThrow();
    await expect(seal(content, sender, [{ record: { ...receiver.record, encryption_public_key: outsider.record.encryption_public_key }, expected: receiver.record.fingerprint }])).rejects.toThrow();
  });
  it('rejects wrong passwords, recovery codes and identity-bound vault swaps', async () => {
    await expect(unlock(sender.record, 'wrong password')).rejects.toThrow();
    await expect(recover(sender.record, b64(new Uint8Array(32)), password)).rejects.toThrow();
    await expect(unlock({ ...sender.record, user_id: 99 }, password)).rejects.toThrow();
  });
  it('recovers the same identity and decrypts old documents after password change', async () => {
    const doc = delivered(await encrypted()), newPassword = 'another independent passphrase';
    const update = await recover(sender.record, recoveryCode, newPassword);
    const record: KeyRecord = { ...sender.record, vault: update.vault };
    const restored = await unlock(record, newPassword);
    expect(await fingerprint(restored.record)).toBe(sender.record.fingerprint);
    expect(await open(doc, restored, sender.record, sender.record.fingerprint)).toEqual(content);
    await expect(unlock(record, password)).rejects.toThrow();
  });
  it('uses fresh content keys, UUIDs and nonces per document', async () => {
    const first = await encrypted(), second = await encrypted();
    expect(first.id).not.toBe(second.id); expect(first.nonce).not.toBe(second.nonce);
    expect(first.ciphertext).not.toBe(second.ciphertext); expect(first.envelopes[0].wrapped_key).not.toBe(second.envelopes[0].wrapped_key);
  });
  it('refuses weak passphrases and oversized packages', async () => {
    await expect(createIdentity(9, 'short')).rejects.toThrow('confidential.passwordPolicy');
    await expect(seal({ ...content, note: 'a'.repeat(16 * 1024 * 1024) }, sender, [])).rejects.toThrow('confidential.tooLarge');
  });
  it('does not open a revoked envelope in a current server delivery', async () => {
    const doc = delivered(await encrypted()); doc.envelopes.find(e => e.key_id === receiver.record.id)!.revoked = true;
    await expect(open(doc, receiver, sender.record, sender.record.fingerprint)).rejects.toThrow();
  });
});
