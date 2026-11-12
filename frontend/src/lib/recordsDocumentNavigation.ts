import type { Dossier, DocumentType, EntityId } from '@app-types/records';

export type DocumentDirection = 'DEN' | 'DI';

function entityId(value: EntityId | undefined): string {
  if (typeof value === 'number' && !Number.isSafeInteger(value)) throw new Error('Invalid record ID');
  const id = String(value);
  if (!/^[1-9]\d*$/.test(id)) throw new Error('Invalid record ID');
  return id;
}

function dossierName(dossier: Dossier): string {
  const name = dossier.ten_ho_so.trim();
  if (!name) throw new Error('Missing dossier name');
  return name;
}

export function categoryDossierId(category: DocumentType): string {
  return entityId(typeof category.ho_so === 'object' ? category.ho_so?.id : category.ho_so);
}

export function dossierDocumentTypesDestination(dossier: Dossier): string {
  const query = new URLSearchParams({ ten_ho_so: dossierName(dossier) });
  return `/records/${entityId(dossier.id)}/document-types?${query}`;
}

// IDs select records; the API-confirmed name provides readable context only.
export function documentListDestination(
  category: DocumentType,
  dossier: Dossier,
  direction: DocumentDirection,
  restricted = false,
): string {
  const parentId = entityId(dossier.id);
  if (categoryDossierId(category) !== parentId) throw new Error('Document category does not belong to dossier');
  if (direction !== 'DEN' && direction !== 'DI') throw new Error('Invalid document direction');
  const query = new URLSearchParams({
    ho_so: parentId,
    ten_ho_so: dossierName(dossier),
    loai_van_ban: entityId(category.id),
    pham_vi: restricted ? 'HAN_CHE' : 'NOI_BO',
  });
  return `/documents/${direction === 'DEN' ? 'incoming' : 'outgoing'}?${query}`;
}
