import { apiClient } from '@lib/apiClient';

const RESOURCE_FETCH_PAGE_SIZE = 100;
const MAX_RESOURCE_FETCH_PAGES = 200;

/**
 * Tải toàn bộ các trang dữ liệu từ endpoint phân trang DRF (`next !== null`)
 * để đảm bảo không bị cắt danh sách ở mốc 100 bản ghi.
 * Giữ nguyên cấu trúc trả về (null / T[] / { results, ... }) tương thích hoàn toàn với normalizeList.
 */
export async function fetchAllResourcePages<T>(
  baseEndpoint: string,
  label: string,
  pageSize: number = RESOURCE_FETCH_PAGE_SIZE
): Promise<unknown> {
  const separator = baseEndpoint.includes('?') ? '&' : '?';
  const firstPage = await apiClient<unknown>(
    `${baseEndpoint}${separator}page_size=${pageSize}`
  ).catch((err) => {
    console.warn(`Lỗi tải ${label}:`, err);
    return null;
  });

  if (
    !firstPage ||
    typeof firstPage !== 'object' ||
    Array.isArray(firstPage) ||
    !('results' in firstPage) ||
    !Array.isArray((firstPage as { results: unknown }).results)
  ) {
    return firstPage;
  }

  const firstObj = firstPage as {
    count?: number;
    next?: string | null;
    previous?: string | null;
    results: unknown[];
  };

  if (!firstObj.next) {
    return firstPage;
  }

  const mergedResults: T[] = [];
  const seenIds = new Set<unknown>();
  const seenNextUrls = new Set<string>([String(firstObj.next)]);

  const pushUnique = (items: unknown[]) => {
    for (const item of items) {
      if (
        item &&
        typeof item === 'object' &&
        'id' in item &&
        (item as { id: unknown }).id !== undefined &&
        (item as { id: unknown }).id !== null
      ) {
        const itemId = (item as { id: unknown }).id;
        if (seenIds.has(itemId)) continue;
        seenIds.add(itemId);
      }
      mergedResults.push(item as T);
    }
  };

  pushUnique(firstObj.results);

  for (let page = 2; page <= MAX_RESOURCE_FETCH_PAGES; page += 1) {
    let nextPage: unknown;
    try {
      nextPage = await apiClient<unknown>(
        `${baseEndpoint}${separator}page=${page}&page_size=${pageSize}`
      );
    } catch (err) {
      console.warn(`Lỗi tải ${label} trang ${page}:`, err);
      break;
    }

    if (
      !nextPage ||
      typeof nextPage !== 'object' ||
      Array.isArray(nextPage) ||
      !('results' in nextPage) ||
      !Array.isArray((nextPage as { results: unknown }).results)
    ) {
      break;
    }

    const pageObj = nextPage as { next?: string | null; results: unknown[] };
    pushUnique(pageObj.results);

    if (!pageObj.next || typeof pageObj.next !== 'string') {
      break;
    }
    if (seenNextUrls.has(pageObj.next)) {
      break;
    }
    seenNextUrls.add(pageObj.next);
  }

  return {
    ...firstObj,
    next: null,
    results: mergedResults,
  };
}

