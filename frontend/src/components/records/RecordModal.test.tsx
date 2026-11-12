import React from 'react';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setLanguage } from '@i18n/translate';
import RecordModal from './RecordModal';

const focusCases = [
  { mode: 'dossier', editing: false },
  { mode: 'dossier', editing: true },
  { mode: 'documentType', editing: false },
  { mode: 'documentType', editing: true },
] as const;

function FocusHarness({ mode, editing }: (typeof focusCases)[number]) {
  const [open, setOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const common = { open, error, onClose: () => setOpen(false), onSubmit: () => setError('Save failed') };
  return <>
    <button onClick={() => setOpen(true)}>Open editor</button>
    {mode === 'dossier'
      ? <RecordModal {...common} mode="dossier" value={editing ? { id: 1, so_ky_hieu: 'HS', ten_ho_so: 'Dossier' } : null} />
      : <RecordModal {...common} mode="documentType" value={editing ? { id: 2, ten_loai: 'Document type' } : null} />}
    <button>Outside control</button>
  </>;
}

function openStrictEditor(props: (typeof focusCases)[number]) {
  render(<React.StrictMode><FocusHarness {...props} /></React.StrictMode>);
  const opener = screen.getByRole('button', { name: 'Open editor' });
  opener.focus();
  fireEvent.click(opener);
  return opener;
}


describe('RecordModal', () => {
  afterEach(() => {
    cleanup();
    setLanguage('vi');
  });

  describe.each(focusCases)('$mode editing=$editing in StrictMode', (props) => {
    it('focuses the initial field after effect replay and traps both Tab boundaries', () => {
      openStrictEditor(props);
      const dialog = screen.getByRole('dialog');
      expect(within(dialog).getByLabelText(props.mode === 'dossier' ? /Số\/ký hiệu/ : /Tên loại văn bản/)).toHaveFocus();

      const first = within(dialog).getByRole('button', { name: 'Đóng' });
      const last = within(dialog).getByRole('button', { name: props.editing ? 'Lưu thay đổi' : 'Thêm mới' });
      last.focus();
      expect(fireEvent.keyDown(last, { key: 'Tab' })).toBe(false);
      expect(first).toHaveFocus();
      expect(fireEvent.keyDown(first, { key: 'Tab', shiftKey: true })).toBe(false);
      expect(last).toHaveFocus();
    });

    it.each(['cancel', 'close', 'Escape'])('restores the opener after %s and focuses inside on reopen', (action) => {
      const opener = openStrictEditor(props);
      const dialog = screen.getByRole('dialog');
      if (action === 'Escape') fireEvent.keyDown(document.activeElement!, { key: 'Escape' });
      else fireEvent.click(within(dialog).getByRole('button', { name: action === 'cancel' ? 'Hủy' : 'Đóng' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(opener).toHaveFocus();
      fireEvent.click(opener);
      expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement);
    });

    it('keeps focus and input when the parent rerenders with a save error', () => {
      openStrictEditor(props);
      const dialog = screen.getByRole('dialog');
      const field = within(dialog).getByLabelText(props.mode === 'dossier' ? /Số\/ký hiệu/ : /Tên loại văn bản/);
      fireEvent.change(field, { target: { value: 'Changed' } });
      if (props.mode === 'dossier') fireEvent.change(within(dialog).getByLabelText(/Tên hồ sơ/), { target: { value: 'Dossier' } });
      field.focus();
      fireEvent.submit(dialog);
      expect(screen.getByRole('alert')).toHaveTextContent('Save failed');
      expect(field).toHaveValue('Changed');
      expect(field).toHaveFocus();
    });
  });

  it('validates dossier fields in their visual order', () => {
    const onSubmit = vi.fn();
    render(<RecordModal open mode="dossier" onClose={vi.fn()} onSubmit={onSubmit} />);
    const dialog = screen.getByRole('dialog');
    fireEvent.submit(dialog);
    expect(screen.getByRole('alert')).toHaveTextContent('Vui lòng nhập số/ký hiệu hồ sơ.');
    fireEvent.change(screen.getByLabelText(/Số\/ký hiệu/), { target: { value: 'HS' } });
    fireEvent.change(screen.getByLabelText(/Thứ tự ưu tiên/), { target: { value: '0' } });
    fireEvent.submit(dialog);
    expect(screen.getByRole('alert')).toHaveTextContent('Số thứ tự ưu tiên phải là số nguyên dương.');
    fireEvent.change(screen.getByLabelText(/Thứ tự ưu tiên/), { target: { value: '1' } });
    fireEvent.submit(dialog);
    expect(screen.getByRole('alert')).toHaveTextContent('Vui lòng nhập tên hồ sơ.');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('rejects priority zero before calling the API', () => {
    const onSubmit = vi.fn();
    render(
      <RecordModal
        open
        mode="dossier"
        value={null}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    fireEvent.change(screen.getByLabelText(/Số\/ký hiệu/), {
      target: { value: 'HS-001' },
    });
    fireEvent.change(screen.getByLabelText(/Thứ tự ưu tiên/), {
      target: { value: '0' },
    });
    fireEvent.change(screen.getByLabelText(/Tên hồ sơ/), {
      target: { value: 'Hồ sơ kiểm thử' },
    });
    fireEvent.submit(screen.getByRole('dialog'));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Số thứ tự ưu tiên phải là số nguyên dương.'
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('renders translated controls when English is selected', () => {
    act(() => setLanguage('en'));
    render(
      <RecordModal
        open
        mode="dossier"
        value={null}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByRole('heading', { name: 'Add dossier' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Reference/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add new' })).toBeInTheDocument();
  });

  it('submits the document type date and note after native input events', () => {
    act(() => setLanguage('en'));
    const onSubmit = vi.fn();
    render(<RecordModal open mode="documentType" value={null} onClose={vi.fn()} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/Document type name/), { target: { value: '  New category  ' } });
    fireEvent.input(screen.getByLabelText(/date/i), { target: { value: '2026-10-15' } });
    fireEvent.change(screen.getByRole('textbox', { name: /note/i }), { target: { value: '  Updated note  ' } });
    fireEvent.submit(screen.getByRole('dialog'));
    expect(onSubmit).toHaveBeenCalledWith({ ten_loai: 'New category', ngay_lap: '2026-10-15', ghi_chu: 'Updated note' });
  });
});
