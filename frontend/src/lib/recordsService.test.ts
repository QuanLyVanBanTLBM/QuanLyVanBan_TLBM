import { describe, expect, it } from 'vitest';
import { normalizePage } from '@lib/recordsService';

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
