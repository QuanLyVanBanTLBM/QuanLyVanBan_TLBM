import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import { Card, Button } from '@components/common';

interface PasswordChangePageProps {
  onNavigate?: (page: ActivePageId) => void;
}

export default function PasswordChangePage({ onNavigate }: PasswordChangePageProps) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [currentPass, setCurrentPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');

  const [showCurrentPass, setShowCurrentPass] = useState(false);
  const [showNewPass, setShowNewPass] = useState(false);
  const [showConfirmPass, setShowConfirmPass] = useState(false);

  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Tính toán độ mạnh mật khẩu thực tế (0 - 4)
  const hasMinLength = newPass.length >= 8;
  const hasMixedCase = /[A-Z]/.test(newPass) && /[a-z]/.test(newPass);
  const hasNumber = /[0-9]/.test(newPass);
  const hasSpecial = /[^A-Za-z0-9]/.test(newPass);

  const strengthScore = [hasMinLength, hasMixedCase, hasNumber, hasSpecial].filter(Boolean).length;

  const getStrengthLabel = () => {
    if (!newPass) return null;
    switch (strengthScore) {
      case 1:
        return { label: t('passwordChange.strengthWeak'), color: 'bg-danger', text: 'text-danger' };
      case 2:
        return { label: t('passwordChange.strengthFair'), color: 'bg-warning', text: 'text-warning' };
      case 3:
        return { label: t('passwordChange.strengthGood'), color: 'bg-primary', text: 'text-primary' };
      case 4:
        return { label: t('passwordChange.strengthStrong'), color: 'bg-success', text: 'text-success' };
      default:
        return { label: t('passwordChange.strengthWeak'), color: 'bg-danger', text: 'text-danger' };
    }
  };

  const strengthInfo = getStrengthLabel();
  const isMatch = confirmPass.length > 0 && confirmPass === newPass;
  const isMismatch = confirmPass.length > 0 && confirmPass !== newPass;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentPass || !newPass || !confirmPass) {
      setFeedbackMsg({ type: 'error', text: t('passwordChange.emptyError') });
      return;
    }

    if (newPass.length < 8) {
      setFeedbackMsg({ type: 'error', text: t('passwordChange.tooShortError') });
      return;
    }

    if (newPass !== confirmPass) {
      setFeedbackMsg({ type: 'error', text: t('passwordChange.mismatchError') });
      return;
    }

    const token =
      localStorage.getItem('tlbm_token') ||
      (() => {
        try {
          return JSON.parse(localStorage.getItem('tlbm_session') || '{}')?.token;
        } catch {
          return null;
        }
      })();

    if (!token) {
      setFeedbackMsg({
        type: 'error',
        text: 'Chưa tìm thấy phiên đăng nhập hợp lệ. Vui lòng đăng nhập lại trước khi đổi mật khẩu!',
      });
      return;
    }

    setIsLoading(true);
    setFeedbackMsg(null);

    try {
      const response = await fetch('/api/auth/change-password/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          old_password: currentPass,
          new_password: newPass,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.success === false) {
        setIsLoading(false);
        const errorMsg =
          data.detail ||
          data.message ||
          data.error ||
          (data.old_password && data.old_password[0]) ||
          (data.new_password && data.new_password[0]) ||
          'Mật khẩu hiện tại không chính xác hoặc không đáp ứng yêu cầu bảo mật.';
        setFeedbackMsg({ type: 'error', text: errorMsg });
        return;
      }

      setIsLoading(false);
      setFeedbackMsg({
        type: 'success',
        text: data.message || data.detail || t('passwordChange.successMsg'),
      });
      setCurrentPass('');
      setNewPass('');
      setConfirmPass('');
    } catch {
      setIsLoading(false);
      setFeedbackMsg({
        type: 'error',
        text: 'Không thể kết nối đến máy chủ xác thực. Vui lòng thử lại sau!',
      });
    }
  };

  return (
    <div className="max-w-4xl mx-auto my-5 flex flex-col gap-5">
      <Card className="p-6 sm:p-8">
        {/* Header trang Thiết lập mật khẩu */}
        <div className="flex justify-between items-start border-b border-border-subtle pb-5 mb-6 flex-wrap gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-xl shadow-xs">
              <i className="fa-solid fa-key" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-main m-0 flex items-center gap-2">
                <span>{t('passwordChange.title')}</span>
              </h1>
              <p className="text-xs text-secondary mt-1 max-w-xl">
                {t('passwordChange.subtitle')}
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-surface-elevated border border-border-subtle text-text-muted flex items-center gap-1.5">
            <i className="fa-solid fa-shield-check text-emerald-500" />
            <span>{t('passwordChange.moduleTag')}</span>
          </span>
        </div>

        {/* Thông báo kết quả (Success / Error banner) */}
        {feedbackMsg && (
          <div
            className={`p-3.5 rounded-xl text-xs font-semibold flex items-center justify-between gap-3 mb-6 animate-in fade-in duration-200 ${
              feedbackMsg.type === 'success'
                ? 'bg-success/10 border border-success/30 text-success'
                : 'bg-danger/10 border border-danger/30 text-danger'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <i className={`fa-solid ${feedbackMsg.type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'} text-sm`} />
              <span>{feedbackMsg.text}</span>
            </div>
            <button
              type="button"
              onClick={() => setFeedbackMsg(null)}
              className="text-text-muted hover:text-main cursor-pointer"
              title="Đóng thông báo"
            >
              <i className="fa-solid fa-xmark" />
            </button>
          </div>
        )}

        {/* Bố cục 2 cột cân đối: Form bên trái (60%) & Quy chuẩn bên phải (40%) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Cột trái: Form nhập liệu */}
          <form onSubmit={handleSubmit} className="lg:col-span-7 flex flex-col gap-4">
            {/* 1. Mật khẩu hiện tại */}
            <div>
              <label className="text-xs font-bold text-main block mb-1.5">
                {t('passwordChange.currentPassword')} <span className="text-danger">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted text-xs">
                  <i className="fa-solid fa-lock" />
                </div>
                <input
                  type={showCurrentPass ? 'text' : 'password'}
                  placeholder={t('passwordChange.currentPasswordPlaceholder')}
                  value={currentPass}
                  onChange={(e) => setCurrentPass(e.target.value)}
                  className="w-full pl-9 pr-10 py-2.5 rounded-lg border border-border-subtle bg-surface-elevated text-main text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors placeholder:text-muted"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPass(!showCurrentPass)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-main transition-colors cursor-pointer text-xs"
                  title={showCurrentPass ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                >
                  <i className={`fa-solid ${showCurrentPass ? 'fa-eye-slash' : 'fa-eye'}`} />
                </button>
              </div>
            </div>

            {/* 2. Mật khẩu mới */}
            <div>
              <label className="text-xs font-bold text-main block mb-1.5">
                {t('passwordChange.newPassword')} <span className="text-danger">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted text-xs">
                  <i className="fa-solid fa-shield-keyhole" />
                </div>
                <input
                  type={showNewPass ? 'text' : 'password'}
                  placeholder={t('passwordChange.newPasswordPlaceholder')}
                  value={newPass}
                  onChange={(e) => setNewPass(e.target.value)}
                  className="w-full pl-9 pr-10 py-2.5 rounded-lg border border-border-subtle bg-surface-elevated text-main text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors placeholder:text-muted"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPass(!showNewPass)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-main transition-colors cursor-pointer text-xs"
                  title={showNewPass ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                >
                  <i className={`fa-solid ${showNewPass ? 'fa-eye-slash' : 'fa-eye'}`} />
                </button>
              </div>

              {/* Thanh đo độ mạnh mật khẩu (Password Strength Meter) */}
              {newPass && strengthInfo && (
                <div className="mt-2 flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-secondary">Độ mạnh:</span>
                    <span className={`font-bold ${strengthInfo.text}`}>{strengthInfo.label}</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-elevated border border-border-subtle rounded-full overflow-hidden flex gap-1">
                    <div className={`h-full flex-1 rounded-full transition-all ${strengthScore >= 1 ? strengthInfo.color : 'bg-transparent'}`} />
                    <div className={`h-full flex-1 rounded-full transition-all ${strengthScore >= 2 ? strengthInfo.color : 'bg-transparent'}`} />
                    <div className={`h-full flex-1 rounded-full transition-all ${strengthScore >= 3 ? strengthInfo.color : 'bg-transparent'}`} />
                    <div className={`h-full flex-1 rounded-full transition-all ${strengthScore >= 4 ? strengthInfo.color : 'bg-transparent'}`} />
                  </div>
                </div>
              )}
            </div>

            {/* 3. Xác nhận mật khẩu mới */}
            <div>
              <label className="text-xs font-bold text-main block mb-1.5">
                {t('passwordChange.confirmPassword')} <span className="text-danger">*</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted text-xs">
                  <i className="fa-solid fa-circle-check" />
                </div>
                <input
                  type={showConfirmPass ? 'text' : 'password'}
                  placeholder={t('passwordChange.confirmPasswordPlaceholder')}
                  value={confirmPass}
                  onChange={(e) => setConfirmPass(e.target.value)}
                  className={`w-full pl-9 pr-10 py-2.5 rounded-lg border bg-surface-elevated text-main text-xs focus:outline-none transition-colors placeholder:text-muted ${
                    isMatch
                      ? 'border-success focus:border-success focus:ring-1 focus:ring-success'
                      : isMismatch
                      ? 'border-danger focus:border-danger focus:ring-1 focus:ring-danger'
                      : 'border-border-subtle focus:border-primary focus:ring-1 focus:ring-primary'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPass(!showConfirmPass)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-main transition-colors cursor-pointer text-xs"
                  title={showConfirmPass ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                >
                  <i className={`fa-solid ${showConfirmPass ? 'fa-eye-slash' : 'fa-eye'}`} />
                </button>
              </div>

              {/* Phản hồi trạng thái khớp mật khẩu */}
              {isMatch && (
                <div className="text-[11px] text-success mt-1 flex items-center gap-1">
                  <i className="fa-solid fa-check text-[10px]" />
                  <span>Mật khẩu xác nhận hoàn toàn khớp</span>
                </div>
              )}
              {isMismatch && (
                <div className="text-[11px] text-danger mt-1 flex items-center gap-1">
                  <i className="fa-solid fa-xmark text-[10px]" />
                  <span>Mật khẩu xác nhận không khớp</span>
                </div>
              )}
            </div>

            {/* Cụm nút hành động */}
            <div className="flex items-center gap-3 pt-3 flex-wrap">
              <Button
                type="submit"
                variant="primary"
                size="md"
                icon={isLoading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-floppy-disk'}
                disabled={isLoading || !currentPass || !newPass || !confirmPass || isMismatch}
              >
                {isLoading ? 'Đang cập nhật...' : t('passwordChange.submitBtn')}
              </Button>

              <Button
                type="button"
                variant="secondary"
                size="md"
                icon="fa-solid fa-arrow-left"
                onClick={() => {
                  if (onNavigate) onNavigate('dashboard');
                  navigate('/dashboard');
                }}
              >
                {t('passwordChange.backBtn')}
              </Button>
            </div>
          </form>

          {/* Cột phải: Bảng quy chuẩn an toàn mật khẩu */}
          <div className="lg:col-span-5 bg-surface-elevated/70 border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-xs font-bold text-main border-b border-border-subtle pb-3">
              <i className="fa-solid fa-shield-halved text-primary" />
              <span>{t('passwordChange.securityGuidelinesTitle')}</span>
            </div>

            <div className="flex flex-col gap-2.5 text-xs">
              <div className={`flex items-start gap-2 transition-colors ${hasMinLength ? 'text-success font-semibold' : 'text-secondary'}`}>
                <i className={`fa-solid ${hasMinLength ? 'fa-circle-check text-success' : 'fa-circle-dot text-muted'} mt-0.5 text-[11px]`} />
                <span>{t('passwordChange.ruleMinLength')}</span>
              </div>

              <div className={`flex items-start gap-2 transition-colors ${hasMixedCase ? 'text-success font-semibold' : 'text-secondary'}`}>
                <i className={`fa-solid ${hasMixedCase ? 'fa-circle-check text-success' : 'fa-circle-dot text-muted'} mt-0.5 text-[11px]`} />
                <span>{t('passwordChange.ruleMixedCase')}</span>
              </div>

              <div className={`flex items-start gap-2 transition-colors ${hasNumber ? 'text-success font-semibold' : 'text-secondary'}`}>
                <i className={`fa-solid ${hasNumber ? 'fa-circle-check text-success' : 'fa-circle-dot text-muted'} mt-0.5 text-[11px]`} />
                <span>{t('passwordChange.ruleNumber')}</span>
              </div>

              <div className={`flex items-start gap-2 transition-colors ${hasSpecial ? 'text-success font-semibold' : 'text-secondary'}`}>
                <i className={`fa-solid ${hasSpecial ? 'fa-circle-check text-success' : 'fa-circle-dot text-muted'} mt-0.5 text-[11px]`} />
                <span>{t('passwordChange.ruleSpecial')}</span>
              </div>

              <div className="flex items-start gap-2 text-secondary">
                <i className="fa-solid fa-circle-info text-muted mt-0.5 text-[11px]" />
                <span>{t('passwordChange.ruleNoPersonal')}</span>
              </div>

              <div className="flex items-start gap-2 text-secondary">
                <i className="fa-solid fa-clock-rotate-left text-muted mt-0.5 text-[11px]" />
                <span>{t('passwordChange.rulePeriodic')}</span>
              </div>
            </div>

            <div className="mt-2 pt-3 border-t border-border-subtle/80 text-[11px] text-muted flex items-start gap-2 leading-relaxed">
              <i className="fa-solid fa-headset text-primary shrink-0 mt-0.5" />
              <span>
                {t('passwordChange.helpHotline')}
              </span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}



