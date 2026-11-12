import { describe, expect, it } from 'vitest';
import { categoryDossierId, documentListDestination, dossierDocumentTypesDestination } from './recordsDocumentNavigation';
import { pathToPageId } from './routes';

const dossier = { id: 9, so_ky_hieu: 'HS', ten_ho_so: 'Hồ sơ & Kế hoạch?/2026' };
const category = { id: 23, ho_so: 9, ten_loai: 'Category' };
describe('record context handoff', () => {
  it('encodes the dossier name when opening level two', () => {
    const url = new URL(dossierDocumentTypesDestination(dossier), 'https://local.invalid');
    expect(url.pathname).toBe('/records/9/document-types');
    expect(url.searchParams.get('ten_ho_so')).toBe(dossier.ten_ho_so);
    expect([...url.searchParams.keys()]).toEqual(['ten_ho_so']);
  });
  it.each(['DEN', 'DI'] as const)('passes both authoritative IDs and a readable name for %s', (kind) => {
    const url = new URL(documentListDestination(category, dossier, kind), 'https://local.invalid');
    expect(url.pathname).toBe(`/documents/${kind === 'DEN' ? 'incoming' : 'outgoing'}`);
    expect(Object.fromEntries(url.searchParams)).toEqual({ ho_so: '9', ten_ho_so: dossier.ten_ho_so, loai_van_ban: '23', pham_vi: 'NOI_BO' });
    expect(new URL(documentListDestination(category, dossier, kind, true), 'https://local.invalid').searchParams.get('pham_vi')).toBe('HAN_CHE');
  });
  it('accepts nested dossier relations without trusting the nested name', () => {
    expect(categoryDossierId({ ...category, ho_so: { ...dossier, ten_ho_so: 'Old name' } })).toBe('9');
    expect(documentListDestination({ ...category, ho_so: dossier }, dossier, 'DEN')).toContain('loai_van_ban=23');
  });
  it.each(['0', '-1', '9&other=1', '01', '', 'NaN'])('rejects invalid primary key %s', (id) => {
    expect(() => dossierDocumentTypesDestination({ ...dossier, id })).toThrow();
    expect(() => documentListDestination({ ...category, id }, dossier, 'DEN')).toThrow();
    expect(() => categoryDossierId({ ...category, ho_so: id })).toThrow();
  });
  it('rejects missing, mismatched or unsafe context', () => {
    expect(() => categoryDossierId({ id: 23, ten_loai: 'Category' })).toThrow();
    expect(() => documentListDestination(category, { ...dossier, id: 10 }, 'DEN')).toThrow();
    expect(() => documentListDestination(category, { ...dossier, ten_ho_so: '  ' }, 'DI')).toThrow();
    expect(() => dossierDocumentTypesDestination({ ...dossier, id: Number.MAX_SAFE_INTEGER + 1 })).toThrow();
  });
  it('keeps existing route-to-tab mappings', () => {
    expect(pathToPageId('/records/document-types')).toBe('record_types');
    expect(pathToPageId('/records/9/document-types')).toBe('record_types');
    expect(pathToPageId('/records')).toBe('records');
  });
});
