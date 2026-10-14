// @vitest-environment node
import { expect, it } from 'vitest';
import { createIdentity, open, seal, unlock } from './crypto';
import type { KeyRecord } from './crypto';

// Opt-in against disposable local fixtures only; never enabled in a production build.
const base = import.meta.env.VITE_CONFIDENTIAL_TEST_URL;
it.skipIf(!base)('WebCrypto interoperates with Django signatures, JWT access and recovery over real HTTP', async () => {
  const ownerToken = import.meta.env.VITE_CONFIDENTIAL_TEST_OWNER_TOKEN;
  const recipientToken = import.meta.env.VITE_CONFIDENTIAL_TEST_RECIPIENT_TOKEN;
  async function request(path: string, token: string, body?: unknown, method = body ? 'POST' : 'GET') {
    const response = await fetch(`${base}${path}`, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    const value = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(value)}`);
    return value;
  }
  const password = 'independent integration passphrase';
  const ownerState = await request('/key/', ownerToken), recipientState = await request('/key/', recipientToken);
  const senderIdentity = await createIdentity(ownerState.user_id, password), recipientIdentity = await createIdentity(recipientState.user_id, password);
  await request('/key/', ownerToken, senderIdentity.registration);
  await request('/key/', recipientToken, recipientIdentity.registration);
  const senderRecord: KeyRecord = (await request('/key/', ownerToken)).key;
  const recipientRecord: KeyRecord = (await request('/key/', recipientToken)).key;
  const sender = await unlock(senderRecord, password), recipient = await unlock(recipientRecord, password);
  const content = { number: 'INTEROP', title: 'Interoperability acceptance', note: 'Known test data only', files: [] };
  const encrypted = await seal(content, sender, [{ record: recipientRecord, expected: recipientRecord.fingerprint }]);
  await request('/documents/', ownerToken, encrypted);
  const delivered = await request(`/documents/${encrypted.id}/`, recipientToken);
  expect(await open(delivered, recipient, senderRecord, senderRecord.fingerprint)).toEqual(content);
  const { recover } = await import('./crypto');
  const update = await recover(senderRecord, senderIdentity.recoveryCode, 'new independent integration passphrase');
  await request('/key/', ownerToken, update, 'PUT');
  const restored = await unlock((await request('/key/', ownerToken)).key, 'new independent integration passphrase');
  expect(await open(delivered, restored, senderRecord, senderRecord.fingerprint)).toEqual(content);
  await request(`/documents/${encrypted.id}/revoke/`, ownerToken, { user_id: recipientRecord.user_id });
  const denied = await fetch(`${base}/documents/${encrypted.id}/`, { headers: { Authorization: `Bearer ${recipientToken}` } });
  expect(denied.status).toBe(404);
}, 30000);
