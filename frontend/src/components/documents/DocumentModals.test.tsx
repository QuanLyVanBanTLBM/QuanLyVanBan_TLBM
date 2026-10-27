import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import React from 'react';
import DocumentDetailModal from './DocumentDetailModal';
import DocumentViewersModal from './DocumentViewersModal';
import DocumentFormModal, { InitialDocType } from './DocumentFormModal';
import apiClient from '@lib/apiClient';
import { setLanguage } from '@i18n/translate';

vi.mock('@lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('DocumentDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('không render gì khi isOpen = false', () => {
    const { container } = render(
      <DocumentDetailModal isOpen={false} onClose={vi.fn()} documentId={1} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('render và nạp dữ liệu chi tiết văn bản thành công', async () => {
    const mockDetail = {
      id: 1,
      loai: 'DEN',
      loai_display: 'Văn bản Đến',
      nam: 2026,
      so_hieu: '15/CV-BGDDT',
      so_thu_tu: 1,
      ngay_den: '2026-09-23T08:00:00Z',
      trich_yeu: 'Hướng dẫn tổ chức thi tuyển sinh',
      noi_ban_hanh: 'Bộ Giáo Dục',
      hieu_luc: 'CON_HIEU_LUC' as const,
      hieu_luc_display: 'Còn hiệu lực',
      hien_thi: true,
      gui_mail_toan_he_thong: false,
      attachments: [
        {
          id: 101,
          file: '/media/test.pdf',
          file_name: 'huongdan.pdf',
          file_size: 204800,
          uploaded_at: '2026-09-23T08:00:00Z',
        },
      ],
      created_at: '2026-09-23T08:00:00Z',
      updated_at: '2026-09-23T08:00:00Z',
    };

    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockDetail);

    render(<DocumentDetailModal isOpen={true} onClose={vi.fn()} documentId={1} />);

    expect(screen.getByText('Chi Tiết Văn Bản Đến')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('15/CV-BGDDT')).toBeInTheDocument();
      expect(screen.getByText('Hướng dẫn tổ chức thi tuyển sinh')).toBeInTheDocument();
      expect(screen.getByText('huongdan.pdf')).toBeInTheDocument();
    });
  });
});

describe('DocumentViewersModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('không render gì khi isOpen = false', () => {
    const { container } = render(
      <DocumentViewersModal isOpen={false} onClose={vi.fn()} documentId={1} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('render danh sách người đã xem từ API thành công', async () => {
    const mockViewersResponse = {
      count: 2,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          user_id: 10,
          username: 'canbo1',
          full_name: 'Nguyễn Văn A',
          chuc_danh: 'Chuyên viên',
          don_vi: 'Phòng Đào Tạo',
          viewed_at: '2026-09-23T10:30:00Z',
        },
        {
          id: 2,
          user_id: 11,
          username: 'canbo2',
          full_name: 'Trần Thị B',
          chuc_danh: 'Trưởng phòng',
          don_vi: 'Phòng Khảo Thí',
          viewed_at: '2026-09-23T11:00:00Z',
        },
      ],
    };

    (apiClient.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockViewersResponse);

    render(<DocumentViewersModal isOpen={true} onClose={vi.fn()} documentId={1} />);

    expect(screen.getByText('Lịch Sử Người Đã Xem Văn Bản')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('2 lượt xem')).toBeInTheDocument();
      expect(screen.getByText('Nguyễn Văn A')).toBeInTheDocument();
      expect(screen.getByText('Trần Thị B')).toBeInTheDocument();
    });
  });
});

describe('DocumentFormModal', () => {
  it('không render gì khi open = false', () => {
    const { container } = render(
      <DocumentFormModal open={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('render đầy đủ 4 phần và các trường bắt buộc khi open = true', async () => {
    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    // Header
    expect(screen.getByText('Thêm Mới Văn Bản Đến')).toBeInTheDocument();

    // 4 Enterprise Sections
    expect(screen.getByText(/1\. Tiếp nhận & Vào sổ công văn/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Nguồn ban hành & Nội dung văn bản/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Ký duyệt & Hiệu lực văn bản/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Phân phối xử lý & Tệp đính kèm/i)).toBeInTheDocument();

    // Core form labels
    expect(screen.getByText(/Số, ký hiệu/i)).toBeInTheDocument();
    expect(screen.getByText(/Cơ quan \/ Đơn vị ban hành/i)).toBeInTheDocument();
    expect(screen.getByText(/Trích yếu nội dung văn bản/i)).toBeInTheDocument();
    expect(screen.getByText(/Trạng thái hiệu lực/i)).toBeInTheDocument();

    // Ở chế độ Thêm mới, người dùng có thể chọn Còn hiệu lực hoặc Hết hiệu lực
    expect(screen.getByText('Còn hiệu lực')).toBeInTheDocument();
    expect(screen.getByText('Hết hiệu lực')).toBeInTheDocument();
    expect(screen.getByText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i)).toBeInTheDocument();

    // Toggles
    expect(screen.getByText('Hiển thị trên hệ thống')).toBeInTheDocument();
    expect(screen.getByText('Gửi email toàn trường')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('-- Chọn đơn vị nhận --')).toBeInTheDocument();
    });
  });

  it('chỉ hiển thị Còn hiệu lực và Hết hiệu lực khi SỬA (không có mục Đã bị thay thế thủ công)', async () => {
    const mockEditDoc = {
      id: 1,
      so_hieu: '15/CV-BGDDT',
      so_thu_tu: 15,
      hieu_luc: 'CON_HIEU_LUC' as const,
      noi_ban_hanh: 'Bộ GD&ĐT',
      trich_yeu: 'Văn bản hướng dẫn',
    };

    render(<DocumentFormModal open={true} initial={mockEditDoc} onClose={vi.fn()} />);

    // Header sửa
    expect(screen.getByText('Cập Nhật Văn Bản Đến')).toBeInTheDocument();
    expect(screen.getByText('3. Ký duyệt & Hiệu lực văn bản')).toBeInTheDocument();
    expect(screen.getByText('Trạng thái hiệu lực')).toBeInTheDocument();

    // Trường "Số đến" phải ở chế độ CHỈ ĐỌC (readOnly) theo đúng yêu cầu spec itc.pdf
    const soDenInput = screen.getByDisplayValue('#15');
    expect(soDenInput).toBeInTheDocument();
    expect(soDenInput).toHaveAttribute('readonly');

    // Các trường khác như Số hiệu, Nơi ban hành, Trích yếu có thể chỉnh sửa bình thường
    const soHieuInput = screen.getByDisplayValue('15/CV-BGDDT');
    expect(soHieuInput).not.toHaveAttribute('readonly');
    const noiBanHanhInput = screen.getByDisplayValue('Bộ GD&ĐT');
    expect(noiBanHanhInput).not.toHaveAttribute('readonly');

    // Khi sửa văn bản: cho phép chọn "Còn hiệu lực", "Còn hiệu lực 1 phần" hoặc "Hết hiệu lực"
    expect(screen.getByRole('option', { name: 'Còn hiệu lực' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Còn hiệu lực 1 phần' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Hết hiệu lực' })).toBeInTheDocument();
    // KHÔNG có mục chọn thủ công "Đã bị thay thế"
    expect(screen.queryByRole('option', { name: 'Đã bị thay thế' })).not.toBeInTheDocument();

    // Đổi trạng thái sang "Hết hiệu lực"
    const hieuLucSelect = screen.getByDisplayValue('Còn hiệu lực');
    fireEvent.change(hieuLucSelect, { target: { value: 'HET_HIEU_LUC' } });
    expect(hieuLucSelect).toHaveValue('HET_HIEU_LUC');

    await waitFor(() => {
      expect(screen.getByText('-- Chọn đơn vị nhận --')).toBeInTheDocument();
    });
  });

  it('tìm kiếm và gợi ý văn bản thay thế khi tick chọn thay thế cho văn bản khác lúc thêm mới', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/api/accounts/staffs/')) {
        return [];
      }
      return {
        results: [
          {
            id: 99,
            so_hieu: '88/QD-SNN',
            trich_yeu: 'Quyết định triển khai dự án',
            noi_ban_hanh: 'Sở Nông Nghiệp',
            loai_display: 'Văn bản Đến',
          },
        ],
      };
    });

    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    // Tick chọn checkbox "Văn bản này thay thế cho văn bản khác trong hệ thống"
    const replaceCheckbox = screen.getByLabelText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i);
    fireEvent.click(replaceCheckbox);

    const input = await screen.findByPlaceholderText(/Nhập số hiệu văn bản.*trích yếu/i);
    expect(input).toBeInTheDocument();

    // Nhập từ khóa
    fireEvent.change(input, { target: { value: '88' } });

    // Hiển thị dropdown gợi ý
    await waitFor(() => {
      expect(screen.getByText('88/QD-SNN')).toBeInTheDocument();
      expect(screen.getByText('Quyết định triển khai dự án')).toBeInTheDocument();
    });

    // Nhấp chọn văn bản gợi ý
    const option = screen.getByText('88/QD-SNN');
    fireEvent.click(option);

    await waitFor(() => {
      expect((input as HTMLInputElement).value).toBe('');
      expect(screen.getByText(/Đã chọn \(1\):/i)).toBeInTheDocument();
    });
  });

  it('hỗ trợ cơ chế rút gọn thông minh khi chọn trên 1 văn bản thay thế (Giải pháp 2: 1 thẻ chính + Hộp thoại danh sách có phân trang 5 mục/trang)', async () => {
    render(
      <DocumentFormModal
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        defaultLoai="DEN"
        initial={{
          id: 1,
          link_thay_the: '10/CV-A, 11/CV-B, 12/CV-C, 13/CV-D, 14/CV-E, 15/CV-F, 16/CV-G',
          hieu_luc: 'CON_HIEU_LUC',
        } as InitialDocType}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Đã chọn \(7\):/i)).toBeInTheDocument();
      expect(screen.getByText('10/CV-A')).toBeInTheDocument();
      expect(screen.getByText(/\+6 văn bản khác/i)).toBeInTheDocument();
    });

    // Bấm badge để mở hộp thoại danh sách chi tiết (Giải pháp 2)
    const expandBadge = screen.getByText(/\+6 văn bản khác/i);
    fireEvent.click(expandBadge);

    // Xác nhận trang 1 hiển thị các mục từ trang 1 và bộ phân trang
    await waitFor(() => {
      expect(screen.getByText(/Danh Sách Văn Bản Bị Thay Thế Đã Chọn \(7\)/i)).toBeInTheDocument();
      expect(screen.getAllByText('10/CV-A').length).toBe(2); // 1 ở form chính, 1 ở modal
      expect(screen.getByText('11/CV-B')).toBeInTheDocument();
      expect(screen.getByText('12/CV-C')).toBeInTheDocument();
      expect(screen.getByText('13/CV-D')).toBeInTheDocument();
      expect(screen.getByText('14/CV-E')).toBeInTheDocument();
      // Mục thuộc trang 2 chưa hiển thị
      expect(screen.queryByText('15/CV-F')).not.toBeInTheDocument();
      expect(screen.queryByText('16/CV-G')).not.toBeInTheDocument();
      // Tuyệt đối không còn dòng chữ nhỏ "Hiển thị ngoài"
      expect(screen.queryByText('Hiển thị ngoài')).not.toBeInTheDocument();
      // Hiển thị Trang 1 / 2
      expect(screen.getByTestId('replacement-pagination-page')).toHaveTextContent('Trang 1 / 2');
    });

    // Bấm chuyển sang trang 2
    const nextPageBtn = screen.getByRole('button', { name: /Trang tiếp theo/i });
    fireEvent.click(nextPageBtn);

    // Xác nhận trang 2 hiển thị các mục còn lại (15/CV-F, 16/CV-G)
    await waitFor(() => {
      expect(screen.getByText('15/CV-F')).toBeInTheDocument();
      expect(screen.getByText('16/CV-G')).toBeInTheDocument();
      // Các mục trang 1 không còn hiển thị trong modal (10/CV-A chỉ còn 1 ở form chính)
      expect(screen.getAllByText('10/CV-A').length).toBe(1);
      expect(screen.queryByText('11/CV-B')).not.toBeInTheDocument();
      expect(screen.queryByText('14/CV-E')).not.toBeInTheDocument();
      // Hiển thị Trang 2 / 2
      expect(screen.getByTestId('replacement-pagination-page')).toHaveTextContent('Trang 2 / 2');
    });

    // Bấm nút Đóng hộp thoại
    const closeBtn = screen.getByRole('button', { name: /^Đóng$/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText(/Danh Sách Văn Bản Bị Thay Thế Đã Chọn/i)).not.toBeInTheDocument();
    });
  });

  it('hiển thị số đến/số đi thực tế ngoài văn bản làm số thứ tự và không còn nhãn Hiển thị ngoài', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/api/accounts/staffs/')) return [];
      if (url.match(/\/api\/documents\/\d+\//)) {
        return {
          id: 1,
          so_hieu: 'VB-TEST',
          link_thay_the: '15/HD-BGDDT, 12/CV-BGDDT',
          hieu_luc: 'CON_HIEU_LUC',
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          results: [
            { id: 101, so_hieu: '15/HD-BGDDT', so_thu_tu: 15, trich_yeu: 'Hướng dẫn đánh giá', noi_ban_hanh: 'Bộ GD&ĐT' },
            { id: 102, so_hieu: '12/CV-BGDDT', so_thu_tu: 12, trich_yeu: 'Tuyển sinh', noi_ban_hanh: 'Bộ GD&ĐT' },
          ],
        };
      }
      return [];
    });

    render(
      <DocumentFormModal
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        defaultLoai="DEN"
        initial={{
          id: 1,
          link_thay_the: '15/HD-BGDDT, 12/CV-BGDDT',
          hieu_luc: 'CON_HIEU_LUC',
        } as InitialDocType}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/\+1 văn bản khác/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/\+1 văn bản khác/i));

    await waitFor(() => {
      expect(screen.getByText(/Danh Sách Văn Bản Bị Thay Thế Đã Chọn/i)).toBeInTheDocument();
      // Tuyệt đối không còn nhãn "Hiển thị ngoài"
      expect(screen.queryByText('Hiển thị ngoài')).not.toBeInTheDocument();
      // Huy hiệu lấy thẳng Số đến thực tế (#15, #12) kèm tooltip Số đến
      const badges15 = screen.getAllByTitle('Số đến: #15');
      expect(badges15.length).toBeGreaterThanOrEqual(1);
      expect(badges15[0]).toHaveTextContent('#15');
      expect(screen.getByTitle('Số đến: #12')).toHaveTextContent('#12');
    });
  });

  it('khóa chọn cán bộ nhận khi chưa chọn đơn vị và chỉ mở khi đã chọn đơn vị nhận', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/api/organizations/units/')) {
        return ['Phòng Hành chính - Tổng hợp', 'Ban công nghệ thông tin'];
      }
      if (url.includes('/api/accounts/staffs/') && url.includes('department=')) {
        return [
          { id: 2, username: 'canbo', ho_ten: 'Trần Cán Bộ', don_vi_ten: 'Phòng Hành chính - Tổng hợp' },
        ];
      }
      return [];
    });

    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    // Ban đầu chưa chọn đơn vị: hiển thị khóa và hướng dẫn
    expect(screen.getByText(/Vui lòng chọn đơn vị nhận trước/i)).toBeInTheDocument();
    expect(screen.getByText(/\(Chưa chọn đơn vị\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/Trần Cán Bộ/i)).not.toBeInTheDocument();

    // Mở dropdown chọn đơn vị nhận
    const unitButton = screen.getByText('-- Chọn đơn vị nhận --');
    fireEvent.click(unitButton);

    // Chọn đơn vị "Phòng Hành chính - Tổng hợp"
    const targetUnitOption = await screen.findByRole('button', { name: /Phòng Hành chính - Tổng hợp/i });
    fireEvent.click(targetUnitOption);

    // Sau khi chọn đơn vị: nạp và hiển thị cán bộ thuộc đơn vị đó
    await waitFor(() => {
      expect(screen.getByText(/Trần Cán Bộ/i)).toBeInTheDocument();
      expect(screen.getByText(/@canbo/i)).toBeInTheDocument();
    });

    // Checkbox cán bộ có thể click
    const staffCheckbox = screen.getByRole('checkbox', { name: /Trần Cán Bộ/i });
    expect(staffCheckbox).not.toBeChecked();
    fireEvent.click(staffCheckbox);
    expect(staffCheckbox).toBeChecked();

    // Khi bấm bỏ chọn đơn vị
    const clearUnitBtn = screen.getByTitle('Bỏ chọn đơn vị');
    fireEvent.click(clearUnitBtn);

    // Quay lại trạng thái khóa và danh sách cán bộ bị ẩn
    await waitFor(() => {
      expect(screen.getByText(/Vui lòng chọn đơn vị nhận trước/i)).toBeInTheDocument();
      expect(screen.queryByText(/Trần Cán Bộ/i)).not.toBeInTheDocument();
    });
  });

  it('phân biệt chính xác hai văn bản trùng số hiệu khi hiển thị văn bản thay thế đã chọn', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/api/accounts/staffs/')) return [];
      if (url.includes('/api/documents/next-so/')) return { next_so: 1 };
      if (url.match(/\/api\/documents\/\d+\//)) {
        return {
          id: 50,
          so_hieu: 'VB-NEW',
          link_thay_the: '1 [Nơi ban hành: Bộ GD&ĐT - Số đến #16]',
          hieu_luc: 'CON_HIEU_LUC',
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          results: [
            { id: 101, so_hieu: '1', so_thu_tu: 15, trich_yeu: 'Công văn 1 Sở', noi_ban_hanh: 'Sở GD&ĐT' },
            { id: 102, so_hieu: '1', so_thu_tu: 16, trich_yeu: 'Công văn 1 Bộ', noi_ban_hanh: 'Bộ GD&ĐT' },
          ],
        };
      }
      return [];
    });

    render(
      <DocumentFormModal
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        defaultLoai="DEN"
        initial={{
          id: 50,
          link_thay_the: '1 [Nơi ban hành: Bộ GD&ĐT - Số đến #16]',
          hieu_luc: 'CON_HIEU_LUC',
        } as InitialDocType}
      />
    );

    // Thẻ văn bản đã chọn hiển thị đúng số hiệu "1", huy hiệu #16 và nơi ban hành "(Bộ GD&ĐT)"
    await waitFor(() => {
      expect(screen.getByText(/Đã chọn \(1\):/i)).toBeInTheDocument();
      expect(screen.getByTitle('Số đến: #16')).toHaveTextContent('#16');
      expect(screen.getByText(/Bộ GD&ĐT/)).toBeInTheDocument();
      // Không bị nhầm lẫn sang Sở GD&ĐT (#15)
      expect(screen.queryByTitle('Số đến: #15')).not.toBeInTheDocument();
      expect(screen.queryByText('Sở GD&ĐT')).not.toBeInTheDocument();
    });

    // Bấm nút xóa tag thay thế
    const removeBtn = screen.getByTitle('Bỏ chọn 1');
    fireEvent.click(removeBtn);

    // Xác nhận đã gỡ bỏ hoàn toàn
    await waitFor(() => {
      expect(screen.queryByTitle('Số đến: #16')).not.toBeInTheDocument();
      expect(screen.queryByText(/Đã chọn \(\d+\):/i)).not.toBeInTheDocument();
    });
  });

  it('allows selecting a document with the same so_hieu when id differs, while preventing self-selection', async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes('/api/documents/next-so/')) return { next_so: 1 };
      if (url.match(/\/api\/documents\/\d+\//)) {
        return {
          id: 50,
          so_hieu: '1',
          so_thu_tu: 16,
          noi_ban_hanh: 'Bộ GD&ĐT',
          hieu_luc: 'CON_HIEU_LUC',
        };
      }
      if (url.includes('/api/documents/')) {
        return {
          results: [
            // Văn bản của Sở (id: 101, so_hieu: '1', #15)
            { id: 101, so_hieu: '1', so_thu_tu: 15, trich_yeu: 'Công văn 1 Sở', noi_ban_hanh: 'Sở GD&ĐT' },
            // Văn bản hiện tại (id: 50, so_hieu: '1', #16)
            { id: 50, so_hieu: '1', so_thu_tu: 16, trich_yeu: 'Công văn 1 Bộ', noi_ban_hanh: 'Bộ GD&ĐT' },
          ],
        };
      }
      return [];
    });

    render(
      <DocumentFormModal
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        defaultLoai="DEN"
        initial={{
          id: 50,
          so_hieu: '1',
          so_thu_tu: 16,
          noi_ban_hanh: 'Bộ GD&ĐT',
          hieu_luc: 'CON_HIEU_LUC',
        } as InitialDocType}
      />
    );

    // Tick chọn checkbox "Văn bản này thay thế cho văn bản khác trong hệ thống"
    const replaceCheckbox = screen.getByLabelText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i);
    fireEvent.click(replaceCheckbox);

    // Mở ô tìm kiếm văn bản thay thế
    const searchInput = await screen.findByPlaceholderText(/Nhập số hiệu văn bản.*trích yếu/i);
    fireEvent.focus(searchInput);
    fireEvent.change(searchInput, { target: { value: '1' } });

    // Văn bản của Sở (#15, id: 101) dù trùng số hiệu "1" vẫn được gợi ý
    await waitFor(() => {
      expect(screen.getByText('Công văn 1 Sở')).toBeInTheDocument();
      expect(screen.getByText('Sở GD&ĐT')).toBeInTheDocument();
      // Văn bản hiện tại (id: 50, Bộ GD&ĐT) bị chặn, không bao giờ xuất hiện trong gợi ý
      expect(screen.queryByText('Công văn 1 Bộ')).not.toBeInTheDocument();
    });

    // Chọn văn bản của Sở (#15)
    const optionBadge = screen.getByTitle('Số đến: #15');
    fireEvent.click(optionBadge);

    // Xác nhận đã chọn văn bản của Sở (#15 - Sở GD&ĐT) làm văn bản thay thế
    await waitFor(() => {
      expect((searchInput as HTMLInputElement).value).toBe('');
      expect(screen.getByPlaceholderText(/Gõ số hiệu hoặc trích yếu để chọn thêm/i)).toBeInTheDocument();
      expect(screen.getByTitle('Bỏ chọn 1')).toBeInTheDocument();
      expect(screen.getAllByText(/Sở GD&ĐT/).length).toBeGreaterThan(0);
    });
  });

  it('hỗ trợ hiển thị đa ngôn ngữ tiếng Anh khi chuyển đổi ngôn ngữ', async () => {
    act(() => {
      setLanguage('en');
    });
    try {
      render(<DocumentFormModal open={true} onClose={vi.fn()} />);
      expect(screen.getByText('Add New Incoming Document')).toBeInTheDocument();
      expect(screen.getByText('1. Receipt & Logging')).toBeInTheDocument();
      expect(screen.getByText('2. Issuing Source & Content')).toBeInTheDocument();
      expect(screen.getByText('3. Approval & Legal Validity')).toBeInTheDocument();
      expect(screen.getByText('4. Distribution & Attachments')).toBeInTheDocument();
      expect(screen.getByText('Save Document')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('-- Select receiving unit --')).toBeInTheDocument();
      });
    } finally {
      act(() => {
        setLanguage('vi');
      });
    }
  });
});


