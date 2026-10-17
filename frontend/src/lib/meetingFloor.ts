/**
 * Tiện ích chuẩn hóa và trích xuất thông tin Tầng cho Phòng họp.
 * Hỗ trợ đa định dạng: 'Tầng 2', 'Lầu 2', 'Floor 2', 'Level 2', 'T2', 'F2', 'Trệt', 'Ground Floor'...
 * Hỗ trợ bản địa hóa Tiếng Việt (Tầng X) và Tiếng Anh (Floor X).
 */

export interface NormalizedFloor {
  key: string;       // Khóa định danh chuẩn hóa, ví dụ: 'G', '1', '2', '3'
  displayNameVi: string; // Tên hiển thị Tiếng Việt: 'Tầng trệt', 'Tầng 2'
  displayNameEn: string; // Tên hiển thị Tiếng Anh: 'Ground Floor', 'Floor 2'
}

/**
 * Trích xuất khóa tầng chuẩn hóa từ chuỗi vị trí phòng họp (location).
 * Ví dụ:
 * - 'Tầng 2, Tòa A' -> '2'
 * - 'Floor 3, Building B' -> '3'
 * - 'T1' -> '1'
 * - 'Lầu 5' -> '5'
 * - 'Tầng trệt' hoặc 'Ground' -> 'G'
 */
export const getFloorKey = (location?: string | null): string | null => {
  if (!location) return null;
  const trimmed = location.trim();

  // 1. Kiểm tra tầng hầm (Basement): B1, B2, Hầm B1, Tầng hầm, Basement...
  const basementWithNum = trimmed.match(/(?:\b(?:t[ầaà]ng\s+)?h[ầaà]m\s*(?:b)?([0-9]+)\b|\bbasement\s*([0-9]+)\b|\bb([0-9]+)\b)/i);
  if (basementWithNum) {
    const num = basementWithNum[1] || basementWithNum[2] || basementWithNum[3];
    return `B${num}`;
  }
  if (/(?:\b(?:t[ầaà]ng\s+)?h[ầaà]m\b|\bbasement\b)/i.test(trimmed)) {
    return 'B';
  }

  // 2. Kiểm tra tầng trệt / ground floor / tầng G
  if (/(?:\b(?:t[ầaà]ng|l[ầaà]u|floor|level)\s+(?:tr[ệe]t|g\b)|\btr[ệe]t\b|\bground(?:\s*floor)?\b)/i.test(trimmed)) {
    return 'G';
  }

  // 3. Kiểm tra tầng lửng (Mezzanine): Tầng lửng, Lửng, Mezzanine, Tầng L, Tầng M...
  if (/(?:\b(?:t[ầaà]ng|l[ầaà]u)\s+(?:l[ửu]ng|[lm]\b)|\bl[ửu]ng\b|\bmezzanine\b)/i.test(trimmed)) {
    return 'M';
  }

  // 4. Kiểm tra các mẫu chuẩn chỉ nhận số: Tầng X, Lầu X, Floor X, Level X
  const standardMatch = trimmed.match(/(?:\bt[ầaà]ng|\bl[ầaà]u|\bfloor|\blevel)\s*([0-9]+)\b/i);
  if (standardMatch) {
    return standardMatch[1];
  }

  // 5. Kiểm tra các mẫu viết tắt: T2, F3, L1
  const shortMatch = trimmed.match(/\b([TFL])([0-9]+)\b/i);
  if (shortMatch) {
    return shortMatch[2];
  }

  return null;
};

/**
 * Định dạng tên tầng theo ngôn ngữ hiện tại.
 */
export const formatFloorName = (floorKey: string, lang: 'vi' | 'en' = 'vi'): string => {
  const isEn = lang === 'en';
  if (floorKey === 'G' || floorKey.toLowerCase() === 'trệt') {
    return isEn ? 'Ground Floor' : 'Tầng trệt';
  }
  if (floorKey === 'M' || floorKey.toLowerCase() === 'lửng') {
    return isEn ? 'Mezzanine' : 'Tầng lửng';
  }
  if (floorKey === 'B' || floorKey.toLowerCase() === 'hầm') {
    return isEn ? 'Basement' : 'Tầng hầm';
  }
  if (floorKey.startsWith('B') && /^[0-9]+$/.test(floorKey.slice(1))) {
    const num = floorKey.slice(1);
    return isEn ? `Basement ${num}` : `Tầng hầm B${num}`;
  }
  return isEn ? `Floor ${floorKey}` : `Tầng ${floorKey}`;
};

/**
 * Hàm trích xuất tên tầng tương thích ngược, nhận ngôn ngữ tùy chọn (mặc định 'vi').
 */
export const extractFloor = (location?: string | null, lang: 'vi' | 'en' = 'vi'): string => {
  const key = getFloorKey(location);
  if (!key) return '';
  return formatFloorName(key, lang);
};

/**
 * Trọng số sắp xếp tầng:
 * - Hầm (B2, B1, B): số âm, B2 (-2) < B1 (-1) < Trệt (0)
 * - Trệt / Ground ('G'): 0
 * - Lửng / Mezzanine ('M'): 0.5
 * - Tầng số nguyên (1, 2, 3...): chính số đó (1, 2, 3...)
 * - Tầng có ký hiệu chữ khác: 999990
 * - Không xác định tầng / null / rỗng: 999999 (đưa về cuối cùng)
 */
export const getFloorWeight = (location?: string | null): number => {
  const key = getFloorKey(location);
  if (!key) return 999999;
  if (key === 'G' || key.toLowerCase() === 'trệt') return 0;
  if (key === 'M' || key.toLowerCase() === 'lửng') return 0.5;
  if (key === 'B' || key.toLowerCase() === 'hầm') return -1;
  if (key.startsWith('B') && /^[0-9]+$/.test(key.slice(1))) {
    const num = parseInt(key.slice(1), 10);
    return -num;
  }
  const num = parseInt(key, 10);
  if (!isNaN(num)) return num;
  return 999990;
};

/**
 * Hàm so sánh sắp xếp danh sách phòng họp theo Tầng tăng dần, sau đó theo tên phòng (A -> Z).
 */
export const compareRoomsByFloor = (
  a: { location?: string | null; name?: string },
  b: { location?: string | null; name?: string }
): number => {
  const weightA = getFloorWeight(a.location);
  const weightB = getFloorWeight(b.location);
  if (weightA !== weightB) {
    return weightA - weightB;
  }
  const keyA = getFloorKey(a.location) || '';
  const keyB = getFloorKey(b.location) || '';
  if (keyA !== keyB) {
    return keyA.localeCompare(keyB, undefined, { numeric: true });
  }
  return (a.name || '').localeCompare(b.name || '', undefined, { numeric: true, sensitivity: 'base' });
};
