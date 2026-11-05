import React, { useMemo } from 'react';
import { useTranslation } from '@i18n/translate';

export interface BirthdayEmployee {
  id: string | number;
  name: string; // Ưu tiên 1: Họ tên
  birthdate: string; // Ưu tiên 2: Ngày tháng sinh nhật
  position: string; // Ưu tiên 3: Chức vụ
  department?: string; // Đơn vị công tác
  isToday?: boolean;
  positionRank?: number; // Thứ tự ưu tiên chức vụ nếu có
}

interface BirthdaysWidgetProps {
  birthdays?: BirthdayEmployee[];
}

/**
 * Trọng số ưu tiên chức vụ dự phòng phía client
 * (Số nhỏ hơn = Chức vụ cao hơn, ưu tiên hiển thị trước).
 */
const POSITION_RANK_FALLBACK: Record<string, number> = {
  'chủ tịch': 1,
  'tổng giám đốc': 2,
  'giám đốc': 3,
  'phó tổng giám đốc': 4,
  'phó giám đốc': 5,
  'trưởng phòng': 6,
  'trưởng ban': 6,
  'trưởng bộ phận': 6,
  'phó phòng': 7,
  'phó ban': 7,
  'phó bộ phận': 7,
  'chuyên viên': 8,
  'nhân viên': 9,
  'văn thư': 10,
};

function getPositionPriority(posName: string = ''): number {
  const normalized = posName.trim().toLowerCase();
  for (const [key, rank] of Object.entries(POSITION_RANK_FALLBACK)) {
    if (normalized.includes(key)) {
      return rank;
    }
  }
  return 50;
}

export default function BirthdaysWidget({
  birthdays = [],
}: BirthdaysWidgetProps) {
  const { t } = useTranslation();

  const formatBirthdate = (dateStr: string) => {
    return dateStr
      .replace('(Hôm nay)', `(${t('dashboardDetails.today') || 'Hôm nay'})`)
      .replace('(Ngày mai)', `(${t('dashboardDetails.tomorrow') || 'Ngày mai'})`);
  };

  // Sắp xếp danh sách sinh nhật theo chức vụ cao đến thấp trước khi hiển thị trên banner
  const sortedBirthdays = useMemo(() => {
    return [...birthdays].sort((a, b) => {
      // 1. Ưu tiên hôm nay trước ngày mai
      const aToday = a.isToday ? 0 : 1;
      const bToday = b.isToday ? 0 : 1;
      if (aToday !== bToday) {
        return aToday - bToday;
      }
      // 2. Ưu tiên chức vụ cao hơn xếp trước (rank nhỏ hơn)
      const rankA = a.positionRank ?? getPositionPriority(a.position);
      const rankB = b.positionRank ?? getPositionPriority(b.position);
      if (rankA !== rankB) {
        return rankA - rankB;
      }
      // 3. Cùng chức vụ -> sắp theo tên
      return (a.name || '').localeCompare(b.name || '', 'vi');
    });
  }, [birthdays]);

  // Nhân đôi danh sách để tạo luồng chạy vô tận mượt mà (-50% translateX)
  const marqueeItems = [...sortedBirthdays, ...sortedBirthdays];

  if (birthdays.length === 0) {
    return null;
  }

  return (
    <div className="bg-surface border border-border-subtle rounded-xl shadow-sm px-4 py-3 flex items-center gap-3.5 overflow-hidden relative select-none">
      {/* Label / Badge cố định bên trái */}
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success text-white text-sm font-bold shrink-0 shadow-xs">
        <i className="fa-solid fa-cake-candles text-xs" />
        <span className="whitespace-nowrap">{t('dashboardDetails.happyBirthday') || 'Chúc mừng sinh nhật:'}</span>
      </div>

      {/* Marquee Viewport with Optical Edge Alpha Masking */}
      <div
        className="relative w-full overflow-hidden flex-1 py-0.5"
        style={{
          maskImage: 'linear-gradient(to right, transparent 0%, black 12px, black calc(100% - 24px), transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to right, transparent 0%, black 12px, black calc(100% - 24px), transparent 100%)',
        }}
      >
        {/* Dải Marquee chạy liên tục */}
        <div className="animate-marquee gap-6 pl-2 items-center">
          {marqueeItems.map((emp, idx) => (
            <div
              key={`${emp.id}-${idx}`}
              className="inline-flex items-center gap-2 text-sm shrink-0 cursor-default"
              title={`${emp.name} - ${emp.birthdate} - ${emp.position} (${emp.department || ''})`}
            >
              {/* 1. ƯU TIÊN: TÊN */}
              <span className="font-bold text-main flex items-center gap-1.5">
                <i className="fa-solid fa-cake-candles text-pink shrink-0 text-xs" />
                <span className="text-primary font-bold">{emp.name}</span>
              </span>

              {/* 2. ƯU TIÊN: NGÀY THÁNG SINH NHẬT */}
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold whitespace-nowrap ${
                  emp.isToday
                    ? 'bg-danger-subtle text-danger border border-danger-border'
                    : 'bg-success-subtle text-success border border-success-border'
                }`}
              >
                {formatBirthdate(emp.birthdate)}
              </span>

              {/* 3. ƯU TIÊN: CHỨC VỤ */}
              <span className="text-secondary text-xs whitespace-nowrap">
                {emp.position}
                {emp.department && (
                  <span className="text-muted"> · {emp.department}</span>
                )}
              </span>

              <span className="text-border-subtle ml-2">•</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
