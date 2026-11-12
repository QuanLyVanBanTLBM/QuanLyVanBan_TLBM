import { describe, expect, it } from 'vitest';
import { giaoNhau, khungSangHopPdf, timNetDut, type HangSo } from './netDut';

const K: HangSo = { save: 10, restore: 11, transform: 12, setDash: 6, constructPath: 91, lenhToNet: [20, 21, 24] };
const DIEN_TICH = 595 * 842;

describe('timNetDut', () => {
  it('chỉ lấy đường nét đứt có tô nét; đường liền và đường chỉ kết thúc bằng endPath bị bỏ', () => {
    const fn = [6, 91, 91, 6, 91, 6, 91];
    const args = [
      [[4, 3], 0], [20, [[]], [100, 500, 310, 620]], [28, [[]], [330, 500, 540, 620]],
      [[], 0], [20, [[]], [50, 300, 150, 350]], [[2, 2], 0], [20, [[]], [50, 100, 150, 150]],
    ];
    expect(timNetDut(fn, args, K, DIEN_TICH)).toEqual([
      { x0: 100, y0: 500, x1: 310, y1: 620 }, { x0: 50, y0: 100, x1: 150, y1: 150 },
    ]);
  });

  it('nhân ma trận hiện hành và khôi phục trạng thái dash theo save/restore', () => {
    const fn = [10, 12, 6, 91, 11, 91];
    const args = [null, [1, 0, 0, 1, 100, 200], [[3], 0], [20, [[]], [0, 0, 50, 40]], null, [20, [[]], [0, 0, 5, 5]]];
    expect(timNetDut(fn, args, K, DIEN_TICH)).toEqual([{ x0: 100, y0: 200, x1: 150, y1: 240 }]);
  });

  it('giữ viền bao phủ hơn nửa trang', () => {
    expect(timNetDut([6, 91], [[[4], 0], [20, [[]], [5, 5, 590, 837]]], K, DIEN_TICH)).toEqual([]);
  });
});

describe('khung ký -> hộp PDF', () => {
  it('đổi % gốc trên-trái sang điểm PDF gốc dưới-trái và kiểm giao nhau', () => {
    const v = khungSangHopPdf({ x: 20, y: 26, w: 22, h: 9 }, 595, 842);
    expect(v.x0).toBeCloseTo(119); expect(v.y1).toBeCloseTo(842 - 218.92);
    expect(giaoNhau({ x0: 100, y0: 500, x1: 310, y1: 620 }, v)).toBe(true);
    expect(giaoNhau({ x0: 50, y0: 100, x1: 150, y1: 150 }, v)).toBe(false);
  });
});
