export interface Position {
  id: number;
  display_order: number;
  name: string;
  is_public: boolean;
  note: string | null;
}

export interface PositionFormData {
  display_order?: number | null;
  name: string;
  is_public: boolean;
  note: string;
}

export interface PositionImportError {
  row: number;
  field: 'display_order' | 'name' | 'is_public';
  code: string;
  value: string;
}

export interface PositionImportResult {
  total: number;
  imported: number;
  failed: number;
  errors: PositionImportError[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
