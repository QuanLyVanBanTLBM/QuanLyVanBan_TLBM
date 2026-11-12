import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import { Button, Badge, Card, CardContent } from '@components/common';

interface PageMeta {
  title: string;
  module: string;
  assignedTeam: string;
  codeRef: string;
  isGroup1: boolean;
  desc: string;
}

interface SyllabusPreviewProps {
  activePage: ActivePageId;
  onNavigate?: (page: ActivePageId) => void;
}

export default function SyllabusPreview({ activePage, onNavigate }: SyllabusPreviewProps) {
  const navigate = useNavigate();
  const { translations } = useTranslation();
  const pageMap = (translations.pages || {}) as Record<ActivePageId, PageMeta>;

  const meta = pageMap[activePage] || {
    title: activePage,
    module: 'Chức năng hệ thống',
    assignedTeam: 'Nhóm 1 (Phân hệ Trang chủ & Quản lý Văn bản)',
    codeRef: 'ITC Django MĐ501911',
    isGroup1: true,
    desc: 'Phân hệ quản lý văn bản & tài liệu mật TLBM.',
  };

  return (
    <div className="max-w-3xl mx-auto my-8 flex flex-col gap-5">
      <Card className="relative overflow-hidden border border-primary/30 shadow-sm">
        <CardContent className="p-7 sm:p-8">
          <div className="flex items-center justify-between flex-wrap gap-2.5 mb-4">
            <div className="flex items-center gap-2.5 flex-wrap">
              <Badge variant="primary" size="md">
                <i className="fa-solid fa-clock-rotate-left mr-1.5" />
                Đang chuẩn bị dữ liệu
              </Badge>
              <Badge variant="secondary" size="md">
                TLBM v2.0
              </Badge>
            </div>
          </div>

          {/* Tiêu đề chức năng */}
          <h1 className="text-2xl font-extrabold text-text-main mt-1 tracking-tight">
            {meta.title}
          </h1>

          {/* Mô tả nghiệp vụ */}
          <p className="text-text-secondary mt-2.5 text-sm leading-relaxed">
            {meta.desc}
          </p>

          {/* Thông báo trạng thái hệ thống */}
          <div className="mt-5 p-4 rounded-xl bg-surface border border-subtle flex flex-col gap-2 text-xs sm:text-sm">
            <div className="flex items-center gap-2">
              <strong className="text-text-main shrink-0 flex items-center gap-1.5">
                <i className="fa-solid fa-thumbtack text-primary text-xs" />
                <span>Bộ phận quản lý:</span>
              </strong>
              <span className="text-primary font-semibold">Ban Quản Trị Hệ Thống TLBM</span>
            </div>

            <div className="flex items-center gap-2">
              <strong className="text-text-main shrink-0 flex items-center gap-1.5">
                <i className="fa-solid fa-circle-info text-info text-xs" />
                <span>Trạng thái:</span>
              </strong>
              <span className="text-text-secondary font-medium">
                Phân hệ đang được hoàn thiện quy trình nghiệp vụ và kết nối dữ liệu máy chủ.
              </span>
            </div>
          </div>

          {/* Nút hành động */}
          <div className="mt-6 flex gap-3 flex-wrap">
            <Button
              variant="primary"
              icon="fa-solid fa-arrow-left"
              onClick={() => {
                if (onNavigate) onNavigate('dashboard');
                navigate('/dashboard');
              }}
            >
              Quay lại Bàn Làm Việc (Trang chủ)
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}



