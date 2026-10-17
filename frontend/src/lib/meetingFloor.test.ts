import { describe, it, expect } from 'vitest';
import {
  getFloorKey,
  formatFloorName,
  extractFloor,
  getFloorWeight,
  compareRoomsByFloor,
} from './meetingFloor';

describe('meetingFloor utility', () => {
  describe('getFloorKey', () => {
    it('nhận diện tầng hầm (Basement) chính xác', () => {
      expect(getFloorKey('Tầng hầm B1')).toBe('B1');
      expect(getFloorKey('Hầm B2')).toBe('B2');
      expect(getFloorKey('Tầng hầm 1')).toBe('B1');
      expect(getFloorKey('Tầng hầm')).toBe('B');
      expect(getFloorKey('Hầm')).toBe('B');
      expect(getFloorKey('Basement 2')).toBe('B2');
      expect(getFloorKey('Basement')).toBe('B');
      expect(getFloorKey('B1, Tòa A')).toBe('B1');
    });

    it('nhận diện tầng trệt chính xác', () => {
      expect(getFloorKey('Tầng trệt')).toBe('G');
      expect(getFloorKey('Lầu trệt')).toBe('G');
      expect(getFloorKey('Ground floor, Building A')).toBe('G');
      expect(getFloorKey('Tầng G')).toBe('G');
    });

    it('nhận diện tầng lửng (Mezzanine) chính xác', () => {
      expect(getFloorKey('Tầng lửng')).toBe('M');
      expect(getFloorKey('Lửng, Tòa B')).toBe('M');
      expect(getFloorKey('Mezzanine')).toBe('M');
      expect(getFloorKey('Tầng M')).toBe('M');
      expect(getFloorKey('Tầng L')).toBe('M');
      expect(getFloorKey('Lầu L')).toBe('M');
    });

    it('nhận diện các tầng số tiêu chuẩn', () => {
      expect(getFloorKey('Tầng 1')).toBe('1');
      expect(getFloorKey('Tầng 2, Tòa A')).toBe('2');
      expect(getFloorKey('Lầu 5')).toBe('5');
      expect(getFloorKey('Floor 3, Building B')).toBe('3');
      expect(getFloorKey('Level 4')).toBe('4');
    });

    it('nhận diện dạng viết tắt T2, F3, L1', () => {
      expect(getFloorKey('T2, Khu C')).toBe('2');
      expect(getFloorKey('F4, Tower 1')).toBe('4');
      expect(getFloorKey('L3')).toBe('3');
    });

    it('trả về null nếu không có thông tin tầng hoặc từ ngữ không phải tầng số', () => {
      expect(getFloorKey(null)).toBeNull();
      expect(getFloorKey(undefined)).toBeNull();
      expect(getFloorKey('')).toBeNull();
      expect(getFloorKey('Tòa nhà văn phòng')).toBeNull();
      expect(getFloorKey('Tòa nhà Floor Plaza')).toBeNull(); // Không nhận diện nhầm Floor Plaza thành tầng Plaza
    });
  });

  describe('formatFloorName & extractFloor', () => {
    it('định dạng tiếng Việt chuẩn cho hầm, trệt, lửng và tầng số', () => {
      expect(formatFloorName('B', 'vi')).toBe('Tầng hầm');
      expect(formatFloorName('B1', 'vi')).toBe('Tầng hầm B1');
      expect(formatFloorName('B2', 'vi')).toBe('Tầng hầm B2');
      expect(formatFloorName('G', 'vi')).toBe('Tầng trệt');
      expect(formatFloorName('M', 'vi')).toBe('Tầng lửng');
      expect(formatFloorName('2', 'vi')).toBe('Tầng 2');

      expect(extractFloor('Tầng hầm B1, Tòa A', 'vi')).toBe('Tầng hầm B1');
      expect(extractFloor('Tầng lửng', 'vi')).toBe('Tầng lửng');
      expect(extractFloor('Tầng 3, Tòa A', 'vi')).toBe('Tầng 3');
      expect(extractFloor('Tầng trệt', 'vi')).toBe('Tầng trệt');
    });

    it('định dạng tiếng Anh chuẩn cho hầm, trệt, lửng và tầng số', () => {
      expect(formatFloorName('B', 'en')).toBe('Basement');
      expect(formatFloorName('B1', 'en')).toBe('Basement 1');
      expect(formatFloorName('B2', 'en')).toBe('Basement 2');
      expect(formatFloorName('G', 'en')).toBe('Ground Floor');
      expect(formatFloorName('M', 'en')).toBe('Mezzanine');
      expect(formatFloorName('2', 'en')).toBe('Floor 2');

      expect(extractFloor('Tầng hầm B1, Tòa A', 'en')).toBe('Basement 1');
      expect(extractFloor('Tầng lửng', 'en')).toBe('Mezzanine');
      expect(extractFloor('Tầng 3, Tòa A', 'en')).toBe('Floor 3');
      expect(extractFloor('Tầng trệt', 'en')).toBe('Ground Floor');
    });
  });

  describe('getFloorWeight', () => {
    it('gán trọng số âm cho tầng hầm (B2 < B1 < 0)', () => {
      expect(getFloorWeight('Hầm B2')).toBe(-2);
      expect(getFloorWeight('Tầng hầm B1')).toBe(-1);
      expect(getFloorWeight('Tầng hầm')).toBe(-1);
      expect(getFloorWeight('Basement')).toBe(-1);
    });

    it('gán trọng số 0 cho Tầng trệt', () => {
      expect(getFloorWeight('Tầng trệt')).toBe(0);
      expect(getFloorWeight('Ground Floor')).toBe(0);
    });

    it('gán trọng số 0.5 cho Tầng lửng (sau Trệt trước Tầng 1)', () => {
      expect(getFloorWeight('Tầng lửng')).toBe(0.5);
      expect(getFloorWeight('Mezzanine')).toBe(0.5);
    });

    it('gán trọng số số nguyên cho các tầng số', () => {
      expect(getFloorWeight('Tầng 1')).toBe(1);
      expect(getFloorWeight('Tầng 2, Tòa A')).toBe(2);
      expect(getFloorWeight('Floor 6')).toBe(6);
    });

    it('gán trọng số 999999 cho phòng không xác định tầng', () => {
      expect(getFloorWeight(null)).toBe(999999);
      expect(getFloorWeight('')).toBe(999999);
      expect(getFloorWeight('Văn phòng tổng hợp')).toBe(999999);
      expect(getFloorWeight('Tòa nhà Floor Plaza')).toBe(999999);
    });
  });

  describe('compareRoomsByFloor', () => {
    it('sắp xếp danh sách phòng theo thứ tự chuẩn kiến trúc: Hầm B2 -> Hầm B1 -> Trệt -> Lửng -> Tầng 1 -> Tầng 2 -> ... -> Không rõ tầng', () => {
      const rooms = [
        { id: 1, name: 'Phòng VIP 601', location: 'Tầng 6' },
        { id: 2, name: 'Phòng Họp 302', location: 'Tầng 3, Tòa Nhà Kỹ thuật' },
        { id: 3, name: 'Phòng Khách VIP', location: null },
        { id: 4, name: 'Phòng Hội trường G', location: 'Tầng trệt' },
        { id: 5, name: 'Phòng Kho Lưu Trữ B2', location: 'Hầm B2' },
        { id: 6, name: 'Phòng Máy Chủ B1', location: 'Tầng hầm B1' },
        { id: 7, name: 'Phòng Không Gian Sáng Tạo', location: 'Tầng lửng' },
        { id: 8, name: 'Phòng 101', location: 'Tầng 1' },
        { id: 9, name: 'Phòng 405', location: 'Tầng 4, Tòa Nhà B' },
      ];

      const sorted = [...rooms].sort(compareRoomsByFloor);

      expect(sorted.map((r) => r.name)).toEqual([
        'Phòng Kho Lưu Trữ B2',       // Trọng số -2 (Hầm B2)
        'Phòng Máy Chủ B1',           // Trọng số -1 (Hầm B1)
        'Phòng Hội trường G',         // Trọng số 0 (Trệt)
        'Phòng Không Gian Sáng Tạo',  // Trọng số 0.5 (Lửng)
        'Phòng 101',                  // Trọng số 1 (Tầng 1)
        'Phòng Họp 302',              // Trọng số 3 (Tầng 3)
        'Phòng 405',                  // Trọng số 4 (Tầng 4)
        'Phòng VIP 601',              // Trọng số 6 (Tầng 6)
        'Phòng Khách VIP',            // Không rõ tầng (999999)
      ]);
    });

    it('cùng tầng thì sắp xếp tên phòng theo thứ tự A -> Z', () => {
      const roomsSameFloor = [
        { name: 'Phòng Họp Ban Giám Đốc (VIP 1)', location: 'Tầng 5, Tòa Nhà A' },
        { name: 'Phòng Ban Giám Đốc (Nội bộ)', location: 'Tầng 5, Tòa A' },
      ];

      const sorted = [...roomsSameFloor].sort(compareRoomsByFloor);
      expect(sorted[0].name).toBe('Phòng Ban Giám Đốc (Nội bộ)');
      expect(sorted[1].name).toBe('Phòng Họp Ban Giám Đốc (VIP 1)');
    });
  });
});
