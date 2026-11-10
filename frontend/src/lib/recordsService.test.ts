import { afterEach, describe, expect, it, vi } from 'vitest';
import { normalizePage, recordsService } from '@lib/recordsService';
import { apiClient } from '@lib/apiClient';

describe('document type detail', () => {
  afterEach(() => vi.restoreAllMocks());
  it.each([false, true])('loads the existing Records endpoint (wrapped: %s)', async (wrapped) => {
    const category = { id: 23, ho_so: 9, ten_loai: 'Category' };
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue(wrapped ? { data: category } : category);
    expect(await recordsService.getDocumentType(category.id)).toEqual(category);
    expect(get).toHaveBeenCalledWith('/api/records/document-types/23/');
  });
});

describe('normalizePage', () => {
  it('normalizes a direct array response', () => {
    expect(normalizePage<{ id: number }>([{ id: 1 }])).toEqual({
      items: [{ id: 1 }],
      count: 1,
      next: null,
      previous: null,
    });
  });

  it('normalizes Django REST Framework pagination', () => {
    expect(
      normalizePage<{ id: number }>({
        count: 21,
        next: '/api/records/dossiers/?page=2',
        previous: null,
        results: [{ id: 1 }],
      })
    ).toEqual({
      items: [{ id: 1 }],
      count: 21,
      next: '/api/records/dossiers/?page=2',
      previous: null,
    });
  });

  it('normalizes a wrapped data response', () => {
    expect(normalizePage<{ id: number }>({ data: { count: 2, results: [{ id: 1 }, { id: 2 }] } })).toEqual({
      items: [{ id: 1 }, { id: 2 }],
      count: 2,
      next: null,
      previous: null,
    });
  });

  it('returns an empty page for an unsupported response', () => {
    expect(normalizePage(null)).toEqual({ items: [], count: 0, next: null, previous: null });
  });
});
