export interface MeetingRoom {
  id: number;
  ten_phong: string;
  vi_tri: string;
  suc_chua: number;
  thiet_bi: string;
  is_public: boolean;
  ghi_chu: string;
  created_at: string;
  updated_at: string;
}

export interface BookingUser {
  id: number;
  username: string;
  full_name: string;
  department: string;
  role: string;
}

export type BookingStatus = 'da_dat' | 'da_huy' | 'hoan_thanh';

export interface MeetingBooking {
  id: number;
  phong_hop: number;
  phong_hop_detail?: MeetingRoom;
  nguoi_dat: number;
  nguoi_dat_detail?: BookingUser;
  don_vi_to_chuc: string;
  tieu_de: string;
  thoi_gian_bat_dau: string;
  thoi_gian_ket_thuc: string;
  so_nguoi_tham_gia: number;
  trang_thai: BookingStatus;
  ghi_chu: string;
  created_at: string;
  updated_at: string;
}

export interface CreateMeetingRoomDTO {
  ten_phong: string;
  vi_tri?: string;
  suc_chua: number;
  thiet_bi?: string;
  is_public?: boolean;
  ghi_chu?: string;
}

export type UpdateMeetingRoomDTO = Partial<CreateMeetingRoomDTO>;

export interface CreateBookingDTO {
  phong_hop: number;
  tieu_de: string;
  don_vi_to_chuc?: string;
  thoi_gian_bat_dau: string;
  thoi_gian_ket_thuc: string;
  so_nguoi_tham_gia?: number;
  ghi_chu?: string;
}

export type UpdateBookingDTO = Partial<CreateBookingDTO> & {
  trang_thai?: BookingStatus;
};
