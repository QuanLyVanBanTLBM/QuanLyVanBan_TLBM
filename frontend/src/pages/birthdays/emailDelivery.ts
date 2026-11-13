import { ApiError } from '@lib/apiClient';

export type DeliveryResult = {
  trang_thai: 'PENDING' | 'SENDING' | 'SUCCESS' | 'FAILED' | 'RETRY';
  delivery_uncertain: boolean;
  employee_name?: string;
  recipient_email?: string;
  sent_at?: string | null;
  delivery_source?: 'AUTO' | 'MANUAL';
};

const ERROR_CODES = [
  'invalidDraft', 'invalidRecipient', 'invalidOccurrence', 'invalidInstruction',
  'previewExpired', 'deliveryConflict', 'recipientChanged', 'smtpUnavailable', 'aiUnavailable',
];

export function birthdayEmailError(error: unknown): string {
  if (error instanceof ApiError) {
    const code = error.data.error;
    if (typeof code === 'string' && ERROR_CODES.includes(code)) {
      return `birthdayPage.manualEmail.errors.${code}`;
    }
    if (error.status === 429) return 'birthdayPage.manualEmail.errors.rateLimited';
    if (error.status === 403) return 'birthdays.messages.permissionDenied';
  }
  return 'birthdayPage.manualEmail.errors.request';
}
