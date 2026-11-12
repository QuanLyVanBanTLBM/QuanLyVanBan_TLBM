/**
 * Type definitions cho phân hệ Phòng họp (Issue #22 - Nhóm 7).
 * Tên field trùng tên cột DDL (meetings_meetingroom, meetings_meetingbooking).
 */

export interface MeetingRoom {
  id: number;
  name: string;
  location: string;
  capacity: number;
  amenities: string | null;
  is_public: boolean;
  trang_thai?: 'AVAILABLE' | 'MAINTENANCE' | 'UNAVAILABLE' | string;
  ghi_chu: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateMeetingRoomDTO {
  name: string;
  location?: string;
  capacity: number;
  amenities?: string;
  is_public?: boolean;
  trang_thai?: 'AVAILABLE' | 'MAINTENANCE' | 'UNAVAILABLE' | string;
  ghi_chu?: string;
}

export type UpdateMeetingRoomDTO = Partial<CreateMeetingRoomDTO>;

export interface BookingUser {
  id: number;
  username: string;
  ho_ten: string;
  don_vi_ten: string;
  chuc_vu_ten: string;
}

export type BookingStatus = 'CONFIRMED' | 'CANCELLED' | 'COMPLETED';

export interface MeetingBooking {
  id: number;
  room: number;
  room_detail?: MeetingRoom;
  organizer: number;
  organizer_detail?: BookingUser;
  department: number | null;
  department_name: string;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  attendees_count: number;
  purpose: string | null;
  cancel_reason?: string | null;
  trang_thai: BookingStatus;
  created_at: string;
}

export interface CreateBookingDTO {
  room: number;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  attendees_count?: number;
  purpose?: string;
}

export type UpdateBookingDTO = Partial<CreateBookingDTO>;

export interface PaginatedResponse<T> {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: T[];
}

