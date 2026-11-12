import { describe, expect, it } from 'vitest';
import { xepKhungKhongChong } from './viTri';

const k = (id: string, trang: number, x: number, y: number, w = 30, h = 10) => ({ id, trang, x, y, w, h });
const giao = (a: ReturnType<typeof k>, b: ReturnType<typeof k>) =>
  a.trang === b.trang && a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

describe('xepKhungKhongChong', () => {
  it('khung cùng vị trí trên cùng trang không còn đè nhau, khung đầu giữ nguyên', () => {
    const kq = xepKhungKhongChong([k('a', 3, 60, 80), k('b', 3, 60, 80), k('c', 3, 60, 80)]);
    expect(kq[0]).toEqual(k('a', 3, 60, 80));
    kq.forEach((x, i) => kq.slice(i + 1).forEach((y) => expect(giao(x, y)).toBe(false)));
    kq.forEach((x) => expect(x.y + x.h).toBeLessThanOrEqual(100));
  });

  it('khung khác trang hoặc không giao nhau giữ nguyên', () => {
    const vao = [k('a', 1, 10, 10), k('b', 2, 10, 10), k('c', 1, 60, 10)];
    expect(xepKhungKhongChong(vao)).toEqual(vao);
  });

  it('hết chỗ phía dưới thì xếp lên trên', () => {
    const kq = xepKhungKhongChong([k('a', 1, 0, 90), k('b', 1, 0, 90)]);
    expect(kq[1].y).toBeLessThan(90);
    expect(giao(kq[0], kq[1])).toBe(false);
  });

  it('không sửa mảng và đối tượng đầu vào', () => {
    const vao = [k('a', 1, 0, 50), k('b', 1, 0, 50)];
    const goc = JSON.stringify(vao);
    xepKhungKhongChong(vao);
    expect(JSON.stringify(vao)).toBe(goc);
  });
});
