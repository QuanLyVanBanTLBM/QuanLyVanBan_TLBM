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
    it('nhận diện tầng trệt chính xác', () => {
      expect(getFloorKey('Tầng trệt')).toBe('G');
      expect(getFloorKey('Lầu trệt')).toBe('G');
      expect(getFloorKey('Ground floor, Building A')).toBe('G');
      expect(getFloorKey('Tầng G')).toBe('G');
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

    it('trả về null nếu không có thông tin tầng', () => {
      expect(getFloorKey(null)).toBeNull();
      expect(getFloorKey(undefined)).toBeNull();
      expect(getFloorKey('')).toBeNull();
      expect(getFloorKey('Tòa nhà văn phòng')).toBeNull();
    });
  });

  describe('formatFloorName & extractFloor', () => {
    it('định dạng tiếng Việt chuẩn', () => {
      expect(formatFloorName('G', 'vi')).toBe('Tầng trệt');
      expect(formatFloorName('2', 'vi')).toBe('Tầng 2');
      expect(extractFloor('Tầng 3, Tòa A', 'vi')).toBe('Tầng 3');
      expect(extractFloor('Tầng trệt', 'vi')).toBe('Tầng trệt');
    });

    it('định dạng tiếng Anh chuẩn', () => {
      expect(formatFloorName('G', 'en')).toBe('Ground Floor');
      expect(formatFloorName('2', 'en')).toBe('Floor 2');
      expect(extractFloor('Tầng 3, Tòa A', 'en')).toBe('Floor 3');
      expect(extractFloor('Tầng trệt', 'en')).toBe('Ground Floor');
    });
  });

  describe('getFloorWeight', () => {
    it('gán trọng số 0 cho Tầng trệt', () => {
      expect(getFloorWeight('Tầng trệt')).toBe(0);
      expect(getFloorWeight('Ground Floor')).toBe(0);
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
    });
  });

  describe('compareRoomsByFloor', () => {
    it('sắp xếp danh sách phòng theo thứ tự tầng tăng dần (Trệt -> Tầng 1 -> Tầng 2 -> ... -> Không rõ tầng)', () => {
      const rooms = [
        { id: 1, name: 'Phòng VIP 601', location: 'Tầng 6' },
        { id: 2, name: 'Phòng Họp 302', location: 'Tầng 3, Tòa Nhà Kỹ thuật' },
        { id: 3, name: 'Phòng Khách VIP', location: null },
        { id: 4, name: 'Phòng Hội trường G', location: 'Tầng trệt' },
        { id: 5, name: 'Phòng 301', location: 'Tầng 3' },
        { id: 6, name: 'Phòng 405', location: 'Tầng 4, Tòa Nhà B' },
        { id: 7, name: 'Phòng Ban Giám Đốc', location: 'Tầng 5, Tòa A' },
      ];

      const sorted = [...rooms].sort(compareRoomsByFloor);

      expect(sorted.map((r) => r.name)).toEqual([
        'Phòng Hội trường G',              // Trọng số 0 (Trệt)
        'Phòng 301',                       // Tầng 3 (chữ cái 'P' vs 'P' -> '301' < 'Họp 302')
        'Phòng Họp 302',                   // Tầng 3
        'Phòng 405',                       // Tầng 4
        'Phòng Ban Giám Đốc',              // Tầng 5
        'Phòng VIP 601',                   // Tầng 6
        'Phòng Khách VIP',                 // Không rõ tầng (999999)
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
