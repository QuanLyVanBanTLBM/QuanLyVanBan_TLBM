import { apiClient } from '@lib/apiClient';
import type {
  Dossier,
  DossierPayload,
  DocumentType,
  DocumentTypePayload,
  EntityId,
  ListQuery,
  PageResult,
} from '@app-types/records';

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
}

export function normalizePage<T>(response: unknown): PageResult<T> {
  if (Array.isArray(response)) {
    return { items: response as T[], count: response.length, next: null, previous: null };
  }

  if (!isRecord(response)) {
    return { items: [], count: 0, next: null, previous: null };
  }

  if (Array.isArray(response.results)) {
    return {
      items: response.results as T[],
      count: Number(response.count ?? response.results.length),
      next: typeof response.next === 'string' ? response.next : null,
      previous: typeof response.previous === 'string' ? response.previous : null,
    };
  }

  if (Array.isArray(response.data)) {
    const pagination = isRecord(response.pagination) ? response.pagination : {};
    return {
      items: response.data as T[],
      count: Number(response.count ?? response.total ?? pagination.total ?? response.data.length),
      next: typeof response.next === 'string' ? response.next : null,
      previous: typeof response.previous === 'string' ? response.previous : null,
    };
  }

  if (isRecord(response.data)) {
    return normalizePage<T>(response.data);
  }

  return { items: [], count: 0, next: null, previous: null };
}

function unwrapEntity<T>(response: unknown): T {
  if (isRecord(response) && isRecord(response.data)) {
    return response.data as T;
  }
  return response as T;
}

function queryString(query: ListQuery): string {
  const params = new URLSearchParams();
  const search = query.search?.trim();
  if (search) params.set('search', search);
  if (query.year) params.set('year', query.year);
  if (query.page && query.page > 1) params.set('page', String(query.page));
  if (query.pageSize) params.set('page_size', String(query.pageSize));
  const value = params.toString();
  return value ? `?${value}` : '';
}

export const recordsService = {
  async listDossiers(query: ListQuery): Promise<PageResult<Dossier>> {
    const response = await apiClient.get<unknown>(`/api/records/dossiers/${queryString(query)}`);
    return normalizePage<Dossier>(response);
  },

  async getDossier(id: EntityId): Promise<Dossier> {
    const response = await apiClient.get<unknown>(`/api/records/dossiers/${id}/`);
    return unwrapEntity<Dossier>(response);
  },

  async createDossier(payload: DossierPayload): Promise<Dossier> {
    const response = await apiClient.post<unknown>('/api/records/dossiers/', payload);
    return unwrapEntity<Dossier>(response);
  },

  async updateDossier(id: EntityId, payload: DossierPayload): Promise<Dossier> {
    const response = await apiClient<unknown>(`/api/records/dossiers/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return unwrapEntity<Dossier>(response);
  },

  async deleteDossier(id: EntityId): Promise<void> {
    await apiClient.delete(`/api/records/dossiers/${id}/`);
  },

  async listDocumentTypes(dossierId: EntityId, query: ListQuery): Promise<PageResult<DocumentType>> {
    const response = await apiClient.get<unknown>(
      `/api/records/dossiers/${dossierId}/document-types/${queryString(query)}`
    );
    return normalizePage<DocumentType>(response);
  },

  async createDocumentType(dossierId: EntityId, payload: DocumentTypePayload): Promise<DocumentType> {
    const response = await apiClient.post<unknown>(
      `/api/records/dossiers/${dossierId}/document-types/`,
      payload
    );
    return unwrapEntity<DocumentType>(response);
  },

  async updateDocumentType(id: EntityId, payload: DocumentTypePayload): Promise<DocumentType> {
    const response = await apiClient<unknown>(`/api/records/document-types/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    return unwrapEntity<DocumentType>(response);
  },

  async deleteDocumentType(id: EntityId): Promise<void> {
    await apiClient.delete(`/api/records/document-types/${id}/`);
  },
};
