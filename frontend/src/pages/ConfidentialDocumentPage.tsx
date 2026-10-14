import { useCallback, useEffect, useRef, useState } from 'react';
import apiClient from '@lib/apiClient';
import { useTranslation } from '@i18n/translate';
import { ApiError } from '@lib/apiClient';
import { b64, createIdentity, fingerprint, MAX_FILE_BYTES, open, recover, seal, unb64, unlock } from '@lib/confidential/crypto';
import type { DeliveredDocument, KeyRecord, PublicKeyRecord, SecretPayload, UnlockedKey } from '@lib/confidential/crypto';

interface KeyState { user_id: number; can_create: boolean; key: KeyRecord | null }
interface Summary { id: string; author_id: number; author_username: string; created_at: string }
type Pending = Awaited<ReturnType<typeof createIdentity>>;
const inputClass = 'w-full border border-border-subtle bg-surface text-main rounded-lg p-2';
const buttonClass = 'border border-border-subtle rounded-lg px-3 py-2 text-main bg-surface disabled:opacity-50';

function saveFile(data: Blob, name: string) {
  const url = URL.createObjectURL(data), link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function ConfidentialDocumentPage() {
  const { t } = useTranslation();
  const [identity, setIdentity] = useState<KeyState | null>(null);
  const [key, setKey] = useState<UnlockedKey | null>(null);
  const [directory, setDirectory] = useState<PublicKeyRecord[]>([]);
  const [pins, setPins] = useState<Record<number, string>>({});
  const [verification, setVerification] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const [password, setPassword] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryBackup, setRecoveryBackup] = useState<KeyRecord | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [savedRecovery, setSavedRecovery] = useState(false);
  const [documents, setDocuments] = useState<Summary[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [payload, setPayload] = useState<SecretPayload>({ number: '', title: '', note: '', files: [] });
  const [files, setFiles] = useState<File[]>([]);
  const [opened, setOpened] = useState<{ doc: DeliveredDocument; payload: SecretPayload } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const epoch = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => () => { epoch.current += 1; }, []);

  const clearSecrets = useCallback(() => {
    epoch.current += 1;
    setKey(null); setOpened(null); setPassword(''); setRecoveryCode(''); setRecoveryBackup(null); setPending(null);
    setPayload({ number: '', title: '', note: '', files: [] }); setFiles([]); setSelected([]);
    setBusy(false); setSavedRecovery(false);
    if (fileInput.current) fileInput.current.value = '';
  }, []);

  const reload = useCallback(async (currentPage: number) => {
    const [own, people, list] = await Promise.all([
      apiClient.get<KeyState>('/api/confidential/key/'),
      apiClient.get<PublicKeyRecord[]>('/api/confidential/directory/'),
      apiClient.get<{ count: number; results: Summary[] }>(`/api/confidential/documents/?page=${currentPage}`),
    ]);
    let cached: Record<number, string> = {};
    try { cached = JSON.parse(localStorage.getItem(`confidential-pins-${own.user_id}`) || '{}'); } catch { /* Require reverification on corrupt storage. */ }
    return { own, people, list, cached };
  }, []);

  useEffect(() => {
    const version = epoch.current;
    let active = true;
    void reload(page).then(({ own, people, list, cached }) => {
      if (!active || version !== epoch.current) return;
      setIdentity(own); setDirectory(people); setDocuments(list.results); setTotal(list.count); setPins(cached);
    }).catch(() => { if (active && version === epoch.current) setError('confidential.loadFailed'); });
    const sessionChanged = () => { clearSecrets(); setIdentity(null); setDirectory([]); setDocuments([]); setPins({}); setVerification({}); };
    const hidden = () => { if (document.hidden) clearSecrets(); };
    window.addEventListener('tlbm_auth_changed', sessionChanged);
    window.addEventListener('storage', sessionChanged);
    document.addEventListener('visibilitychange', hidden);
    return () => {
      active = false;
      window.removeEventListener('tlbm_auth_changed', sessionChanged);
      window.removeEventListener('storage', sessionChanged);
      document.removeEventListener('visibilitychange', hidden);
    };
  }, [page, reload, clearSecrets]);

  useEffect(() => {
    if (!key && !pending) return;
    const timer = setTimeout(clearSecrets, 10 * 60 * 1000);
    return () => clearTimeout(timer);
  }, [key, pending, clearSecrets]);

  async function run<T>(work: () => Promise<T>, done: (value: T) => void) {
    const version = epoch.current;
    setBusy(true); setError('');
    try { const value = await work(); if (version === epoch.current) done(value); }
    catch (cause) {
      if (version === epoch.current) {
        const detail = cause instanceof ApiError ? cause.data.detail : cause instanceof Error ? cause.message : '';
        setError(typeof detail === 'string' && detail.startsWith('confidential.') ? detail : 'confidential.operationFailed');
      }
    } finally { if (version === epoch.current) setBusy(false); }
  }

  async function refreshList() {
    return apiClient.get<{ count: number; results: Summary[] }>(`/api/confidential/documents/?page=${page}`);
  }

  function pinPerson(person: PublicKeyRecord) {
    if (!identity) return;
    void run(async () => {
      const expected = (verification[person.user_id] || '').trim().toLowerCase();
      if (expected !== person.fingerprint || await fingerprint(person) !== expected) throw new Error('confidential.unverifiedKey');
      return { ...pins, [person.user_id]: expected };
    }, value => {
      localStorage.setItem(`confidential-pins-${identity.user_id}`, JSON.stringify(value)); setPins(value);
    });
  }

  async function send() {
    if (!key) return;
    const version = epoch.current;
    await run(async () => {
      if (!payload.title.trim() || !selected.length) throw new Error('confidential.required');
      if (files.reduce((sum, f) => sum + f.size, 0) > MAX_FILE_BYTES || files.length > 10) throw new Error('confidential.tooLarge');
      const attachments = await Promise.all(files.map(async f => ({ name: f.name, data: b64(await f.arrayBuffer()) })));
      const recipients = selected.map(id => {
        const record = directory.find(p => p.user_id === id);
        if (!record || pins[id] !== record.fingerprint) throw new Error('confidential.unverifiedKey');
        return { record, expected: pins[id] };
      });
      const sealed = await seal({ ...payload, files: attachments }, key, recipients);
      if (version !== epoch.current) throw new Error('confidential.operationFailed');
      await apiClient.post('/api/confidential/documents/', sealed);
      return refreshList();
    }, list => {
      setDocuments(list.results); setTotal(list.count);
      setPayload({ number: '', title: '', note: '', files: [] }); setFiles([]); setSelected([]);
      setOpened(null);
      if (fileInput.current) fileInput.current.value = '';
    });
  }

  function showDocument(id: string) {
    if (!key) return;
    void run(async () => {
      const doc = await apiClient.get<DeliveredDocument>(`/api/confidential/documents/${id}/`);
      const author = directory.find(p => p.user_id === doc.author_id);
      if (!author) throw new Error('confidential.unverifiedKey');
      const expected = author.user_id === key.record.user_id ? key.record.fingerprint : pins[author.user_id];
      return { doc, payload: await open(doc, key, author, expected || '') };
    }, setOpened);
  }

  const own = identity?.key;
  const cryptoAvailable = typeof window === 'undefined' || window.isSecureContext !== false;
  return <section className="p-4 space-y-4 text-main" aria-busy={busy}>
    <h1 className="text-2xl font-bold">{t('confidential.title')}</h1>
    <p className="text-secondary">{t('confidential.boundary')}</p>
    {!cryptoAvailable && <div role="alert" className="text-danger">{t('confidential.requireHttps')}</div>}
    {error && <div role="alert" className="text-danger">{t(error)}</div>}
    {!identity && <button className={buttonClass} onClick={() => window.location.reload()}>{t('confidential.reload')}</button>}
    {identity && <div className="border border-border-subtle bg-surface p-4 rounded-lg space-y-3">
      <h2 className="text-lg font-semibold">{t('confidential.personalKey')}</h2>
      {own && <><p>{t('confidential.fingerprint')}</p><code className="break-all block">{own.fingerprint}</code>
        <button className={buttonClass} onClick={() => saveFile(new Blob([JSON.stringify(own)], { type: 'application/json' }), 'confidential-key-backup.json')}>{t('confidential.backup')}</button></>}
      {!key && <>
        <label className="block">{t('confidential.password')}<input className={inputClass} type="password" value={password} disabled={busy || !!pending} maxLength={1024} autoComplete="off" onChange={e => setPassword(e.target.value)} /></label>
        {!own && !pending && <button className={buttonClass} disabled={busy || !cryptoAvailable} onClick={() => void run(() => createIdentity(identity.user_id, password), setPending)}>{t('confidential.createKey')}</button>}
        {pending && <div className="space-y-2">
          <p>{t('confidential.recoveryWarning')}</p><code className="break-all block">{pending.recoveryCode}</code>
          <button className={buttonClass} onClick={() => saveFile(new Blob([pending.recoveryCode], { type: 'text/plain' }), 'confidential-recovery-code.txt')}>{t('confidential.saveRecovery')}</button>
          <label className="block"><input type="checkbox" checked={savedRecovery} onChange={e => setSavedRecovery(e.target.checked)} /> {t('confidential.savedRecovery')}</label>
          <button className={buttonClass} disabled={busy || !savedRecovery} onClick={() => void run(async () => {
            await apiClient.post('/api/confidential/key/', pending.registration);
            return reload(page);
          }, ({ own: state, people, list, cached }) => {
            setIdentity(state); setDirectory(people); setDocuments(list.results); setTotal(list.count); setPins(cached);
            setPending(null); setPassword(''); setSavedRecovery(false);
          })}>{t('confidential.registerKey')}</button>
        </div>}
        {own && <>
          <button className={buttonClass} disabled={busy || !cryptoAvailable} onClick={() => void run(() => unlock(own, password), value => { setKey(value); setPassword(''); setRecoveryCode(''); })}>{t('confidential.unlock')}</button>
          <details><summary>{t('confidential.recover')}</summary>
            <p>{t('confidential.recoveryWarning')}</p>
            <label className="block">{t('confidential.importBackup')}<input type="file" accept="application/json,.json" disabled={busy} onChange={event => {
              const file = event.target.files?.[0];
              if (!file) return;
              void run(async () => {
                if (file.size > 32768) throw new Error('confidential.invalidVault');
                const backup: KeyRecord = JSON.parse(await file.text());
                if (backup.user_id !== own.user_id || backup.fingerprint !== own.fingerprint || await fingerprint(backup) !== own.fingerprint || !backup.vault) throw new Error('confidential.invalidVault');
                return backup;
              }, setRecoveryBackup);
            }} /></label>
            <label className="block">{t('confidential.recoveryCode')}<input className={inputClass} type="password" value={recoveryCode} autoComplete="off" onChange={e => setRecoveryCode(e.target.value)} /></label>
            <button className={buttonClass} disabled={busy} onClick={() => void run(async () => {
              const version = epoch.current;
              const update = await recover(recoveryBackup || own, recoveryCode, password);
              if (version !== epoch.current) throw new Error('confidential.operationFailed');
              await apiClient.put('/api/confidential/key/', update);
              return { ...own, vault: update.vault };
            }, record => { setIdentity({ ...identity, key: record }); setPassword(''); setRecoveryCode(''); setRecoveryBackup(null); })}>{t('confidential.restoreKey')}</button>
          </details>
        </>}
      </>}
      {key && <button className={buttonClass} onClick={clearSecrets}>{t('confidential.lock')}</button>}
    </div>}

    {key && <>
      <div className="border border-border-subtle bg-surface p-4 rounded-lg space-y-3">
        <h2 className="text-lg font-semibold">{t('confidential.contacts')}</h2><p>{t('confidential.verifyHelp')}</p>
        {directory.filter(p => p.user_id !== identity?.user_id).map(person => <div key={person.id} className="border-b border-border-subtle pb-3 space-y-2">
          <strong>{person.username}</strong><code className="break-all block">{person.fingerprint}</code>
          {pins[person.user_id] === person.fingerprint ? <span>{t('confidential.verified')}</span> : <>
            {pins[person.user_id] && <p className="text-danger">{t('confidential.keyChanged')}</p>}
            <label className="block">{t('confidential.expectedFingerprint')}<input className={inputClass} value={verification[person.user_id] || ''} onChange={e => setVerification({ ...verification, [person.user_id]: e.target.value })} /></label>
            <button className={buttonClass} disabled={busy} onClick={() => pinPerson(person)}>{t('confidential.verify')}</button>
          </>}
          {identity?.can_create && <label className="block"><input type="checkbox" disabled={pins[person.user_id] !== person.fingerprint || busy} checked={selected.includes(person.user_id)}
            onChange={e => setSelected(e.target.checked ? [...selected, person.user_id] : selected.filter(id => id !== person.user_id))} /> {t('confidential.recipient')}</label>}
        </div>)}
        {directory.length <= 1 && <p>{t('confidential.noContacts')}</p>}
      </div>
      {identity?.can_create && <form className="border border-border-subtle bg-surface p-4 rounded-lg space-y-3" onSubmit={e => { e.preventDefault(); void send(); }}>
        <h2 className="text-lg font-semibold">{t('confidential.createDocument')}</h2>
        <label className="block">{t('confidential.number')}<input className={inputClass} value={payload.number} maxLength={255} onChange={e => setPayload({ ...payload, number: e.target.value })} /></label>
        <label className="block">{t('confidential.subject')}<input className={inputClass} required maxLength={4000} value={payload.title} onChange={e => setPayload({ ...payload, title: e.target.value })} /></label>
        <label className="block">{t('confidential.note')}<textarea className={inputClass} maxLength={16000} value={payload.note} onChange={e => setPayload({ ...payload, note: e.target.value })} /></label>
        <label className="block">{t('confidential.files')}<input ref={fileInput} className={inputClass} type="file" multiple onChange={e => setFiles(Array.from(e.target.files || []))} /></label>
        <p>{t('confidential.fileLimit')}</p>
        <button className={buttonClass} disabled={busy || !selected.length}>{t('confidential.encryptSend')}</button>
      </form>}
    </>}

    <div className="border border-border-subtle bg-surface p-4 rounded-lg space-y-3">
      <h2 className="text-lg font-semibold">{t('confidential.inbox')}</h2>
      {!key && <p>{t('confidential.lockedHelp')}</p>}
      {documents.length === 0 && <p>{t('confidential.empty')}</p>}
      <ul>{documents.map(doc => <li key={doc.id} className="py-2 flex flex-wrap gap-2 items-center">
        <code className="break-all">{doc.id}</code><span>{doc.author_username}</span><time>{new Date(doc.created_at).toLocaleString()}</time>
        <button className={buttonClass} disabled={!key || busy} onClick={() => showDocument(doc.id)}>{t('confidential.open')}</button>
      </li>)}</ul>
      <button className={buttonClass} disabled={page <= 1 || busy} onClick={() => { setOpened(null); setPage(page - 1); }}>{t('confidential.previous')}</button>
      <span className="px-2">{page}</span>
      <button className={buttonClass} disabled={page * 20 >= total || busy} onClick={() => { setOpened(null); setPage(page + 1); }}>{t('confidential.next')}</button>
    </div>
    {key && opened && <article className="border border-border-subtle bg-surface p-4 rounded-lg space-y-3">
      <h2 className="text-lg font-semibold">{opened.payload.title}</h2><p>{opened.payload.number}</p><p className="whitespace-pre-wrap">{opened.payload.note}</p>
      {opened.payload.files.map((file, index) => <button key={index} className={buttonClass} onClick={() => {
        try { saveFile(new Blob([unb64(file.data)], { type: 'application/octet-stream' }), file.name.replace(/[\\/]/g, '_')); }
        catch { setError('confidential.invalidPayload'); }
      }}>{t('confidential.download')}: {file.name}</button>)}
      {opened.doc.author_id === identity?.user_id && <div><p>{t('confidential.revokeWarning')}</p>
        {opened.doc.envelopes.filter(e => e.user_id !== identity?.user_id && !e.revoked).map(e => <button key={e.key_id} className={buttonClass} disabled={busy} onClick={() => {
          if (!window.confirm(t('confidential.revokeWarning'))) return;
          void run(async () => { await apiClient.post(`/api/confidential/documents/${opened.doc.id}/revoke/`, { user_id: e.user_id }); return refreshList(); }, list => { setOpened(null); setDocuments(list.results); setTotal(list.count); });
        }}>{t('confidential.revoke')}: {directory.find(p => p.user_id === e.user_id)?.username || e.user_id}</button>)}
      </div>}
      <button className={buttonClass} onClick={() => setOpened(null)}>{t('confidential.close')}</button>
    </article>}
  </section>;
}
