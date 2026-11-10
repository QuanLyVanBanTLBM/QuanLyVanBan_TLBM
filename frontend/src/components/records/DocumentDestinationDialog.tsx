import React from 'react';
import { Link } from 'react-router-dom';
import { recordsService } from '@lib/recordsService';
import { Button } from '@components/common';
import { useTranslation } from '@i18n/translate';
import type { Dossier, DocumentType } from '@app-types/records';
import { categoryDossierId, documentListDestination, type DocumentDirection } from '@lib/recordsDocumentNavigation';

interface Props {
  category: DocumentType;
  dossierId?: string;
  onClose: () => void;
  onNavigate: (destination: string) => void;
}

export default function DocumentDestinationDialog({ category, dossierId, onClose, onNavigate }: Props) {
  const { t } = useTranslation();
  const [direction, setDirection] = React.useState<DocumentDirection>('DEN');
  const [restricted, setRestricted] = React.useState(false);
  const dialog = React.useRef<HTMLFormElement>(null);
  const [context, setContext] = React.useState<{
    category: DocumentType; routeId?: string; dossier: Dossier | null; verifiedCategory: DocumentType | null;
  } | null>(null);
  const currentContext = context?.category === category && context.routeId === dossierId ? context : null;
  const destination = currentContext?.dossier && currentContext.verifiedCategory
    ? documentListDestination(currentContext.verifiedCategory, currentContext.dossier, direction, restricted)
    : null;

  React.useEffect(() => {
    let active = true;
    Promise.resolve().then(async () => {
      if (!active) return null;
      const parentId = categoryDossierId(category);
      if (dossierId !== undefined && parentId !== dossierId) throw new Error('Mismatched dossier context');
      const verifiedCategory = await recordsService.getDocumentType(category.id);
      if (!active) return null;
      if (
        String(verifiedCategory.id) !== String(category.id)
        || categoryDossierId(verifiedCategory) !== parentId
        || !verifiedCategory.ten_loai.trim()
      ) throw new Error('Document type context changed');
      const dossier = await recordsService.getDossier(parentId);
      return { dossier, verifiedCategory };
    }).then((result) => {
      if (!active || !result) return;
      documentListDestination(result.verifiedCategory, result.dossier, 'DEN');
      setContext({ category, routeId: dossierId, ...result });
    }).catch(() => {
      if (active) setContext({ category, routeId: dossierId, dossier: null, verifiedCategory: null });
    });
    return () => { active = false; };
  }, [category, dossierId]);

  React.useEffect(() => {
    const previousFocus = document.activeElement;
    dialog.current?.querySelector<HTMLElement>('select')?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      if (event.key === 'Tab') {
        const controls = dialog.current?.querySelectorAll<HTMLElement>('select:not(:disabled), input:not(:disabled), button:not(:disabled), a[href]');
        if (!controls?.length) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => {
      window.removeEventListener('keydown', handleKey);
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4">
      <form ref={dialog} role="dialog" aria-modal="true" aria-labelledby="document-destination-title" aria-describedby="document-destination-context document-destination-note"
        className="w-full max-w-md space-y-4 rounded-xl border border-border-subtle bg-surface p-5 shadow-lg"
        onSubmit={(event) => { event.preventDefault(); if (destination) onNavigate(destination); }}>
        <h2 id="document-destination-title" className="m-0 text-lg font-bold text-main">{t('records.destination.title')}</h2>
        <div id="document-destination-context" aria-live="polite" className="text-sm text-secondary">
          {!currentContext ? <p role="status">{t('records.destination.loadingContext')}</p>
            : currentContext.dossier ? <p>{t('records.common.dossier')}: <strong>{currentContext.dossier.ten_ho_so}</strong></p>
            : <p role="alert">{t('records.destination.contextUnavailable')}</p>}
        </div>
        <p className="text-sm text-secondary">{t('records.documentTypes.name')}: <strong>{currentContext?.verifiedCategory?.ten_loai ?? category.ten_loai}</strong></p>
        <label className="block space-y-2 text-sm text-main">
          <span>{t('records.destination.direction')}</span>
          <select value={direction} onChange={(event) => setDirection(event.target.value as DocumentDirection)}
            className="w-full rounded-lg border border-border-subtle bg-surface px-3 py-2 text-main">
            <option value="DEN">{t('records.documentKinds.vanbanden')}</option>
            <option value="DI">{t('records.documentKinds.vanbandi')}</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-main">
          <input type="checkbox" checked={restricted} onChange={(event) => setRestricted(event.target.checked)} />
          {t('records.destination.restricted')}
        </label>
        <p id="document-destination-note" className="text-xs text-muted">{t('records.destination.note')}</p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>{t('records.actions.cancel')}</Button>
          {destination ? <Link to={destination}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-primary bg-primary px-4 py-2 text-sm font-bold text-white transition hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            <i className="fa-solid fa-arrow-right" aria-hidden="true" />{t('records.actions.viewDocuments')}
          </Link> : <Button type="submit" disabled icon="fa-arrow-right">{t('records.actions.viewDocuments')}</Button>}
        </div>
      </form>
    </div>
  );
}
