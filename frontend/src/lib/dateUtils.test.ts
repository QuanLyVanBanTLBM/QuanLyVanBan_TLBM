import { describe, it, expect } from 'vitest';
import {
  formatDateTime,
  formatDate,
  formatFileSize,
  getFileExtension,
  getFileMeta,
} from './dateUtils';

describe('Date & File Utility Functions (dateUtils)', () => {
  describe('formatDateTime()', () => {
    it('formats valid ISO datetime to HH:mm:ss dd/MM/yyyy', () => {
      // Create a deterministic local date
      const testDate = new Date(2026, 8, 23, 14, 30, 45); // Sept 23, 2026 14:30:45
      const formatted = formatDateTime(testDate.toISOString());
      expect(formatted).toBe('14:30:45 23/09/2026');
    });

    it('returns "—" for null or undefined or empty date', () => {
      expect(formatDateTime(null)).toBe('—');
      expect(formatDateTime(undefined)).toBe('—');
      expect(formatDateTime('')).toBe('—');
    });

    it('returns "—" for invalid date strings', () => {
      expect(formatDateTime('not-a-valid-date')).toBe('—');
    });
  });

  describe('formatDate()', () => {
    it('formats valid date to dd/MM/yyyy', () => {
      const testDate = new Date(2026, 8, 23, 14, 30, 45);
      const formatted = formatDate(testDate.toISOString());
      expect(formatted).toBe('23/09/2026');
    });

    it('returns "—" for null or undefined or empty', () => {
      expect(formatDate(null)).toBe('—');
      expect(formatDate(undefined)).toBe('—');
      expect(formatDate('')).toBe('—');
    });
  });

  describe('formatFileSize()', () => {
    it('formats bytes correctly into human readable units', () => {
      expect(formatFileSize(0)).toBe('0 B');
      expect(formatFileSize(null)).toBe('0 B');
      expect(formatFileSize(512)).toBe('512 B');
      expect(formatFileSize(1024)).toBe('1.0 KB');
      expect(formatFileSize(1048576)).toBe('1.0 MB');
      expect(formatFileSize(1073741824)).toBe('1.0 GB');
    });
  });

  describe('getFileExtension()', () => {
    it('extracts lowercased file extension correctly', () => {
      expect(getFileExtension('cong_van_01.PDF')).toBe('pdf');
      expect(getFileExtension('bao_cao.DOCX')).toBe('docx');
      expect(getFileExtension('file_without_ext')).toBe('');
      expect(getFileExtension('')).toBe('');
      expect(getFileExtension(null)).toBe('');
    });
  });

  describe('getFileMeta()', () => {
    it('identifies PDF files correctly', () => {
      const meta = getFileMeta('quyet_dinh.pdf');
      expect(meta.icon).toBe('fa-file-pdf');
      expect(meta.colorClass).toBe('text-red-500');
      expect(meta.badgeLabel).toBe('PDF');
    });

    it('identifies Word files correctly', () => {
      const meta = getFileMeta('thong_bao.docx');
      expect(meta.icon).toBe('fa-file-word');
      expect(meta.colorClass).toBe('text-blue-500');
      expect(meta.badgeLabel).toBe('WORD');
    });

    it('identifies Excel files correctly', () => {
      const meta = getFileMeta('danh_sach.xlsx');
      expect(meta.icon).toBe('fa-file-excel');
      expect(meta.colorClass).toBe('text-emerald-500');
      expect(meta.badgeLabel).toBe('EXCEL');
    });

    it('identifies Image files correctly', () => {
      const meta = getFileMeta('anh_chu_ky.png');
      expect(meta.icon).toBe('fa-file-image');
      expect(meta.colorClass).toBe('text-purple-500');
      expect(meta.badgeLabel).toBe('ẢNH');
    });

    it('falls back to default icon for unknown file types', () => {
      const meta = getFileMeta('archive.zip');
      expect(meta.icon).toBe('fa-file-lines');
      expect(meta.badgeLabel).toBe('ZIP');
    });
  });
});
