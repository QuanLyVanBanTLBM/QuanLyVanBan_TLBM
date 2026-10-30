import { useEffect, useState } from 'react';
import rawDefaultApiClient, * as allApiClient from '@lib/apiClient';

/**
 * Quyền của user đang đăng nhập (RBAC contract Issue #21), dùng để ẩn/hiện thao tác trên giao diện.
 * Đây không phải lớp bảo mật: backend vẫn kiểm quyền thật ở mọi API.
 */
export interface MyPermissions {
  is_superuser: boolean;
  permissions: string[];
}

let cached: Promise<MyPermissions> | null = null;

type CallableFn = (endpoint: string, options?: RequestInit) => Promise<MyPermissions>;
type ObjectClient = { get: (endpoint: string, options?: RequestInit) => Promise<MyPermissions> };
type CallableClient = CallableFn | ObjectClient;

function isObjectWithGet(val: unknown): val is ObjectClient {
  return typeof val === 'object' && val !== null && 'get' in val && typeof (val as ObjectClient).get === 'function';
}

function getApiClient(): CallableClient | null {
  let named: unknown;
  try {
    named = (allApiClient as Record<string, unknown>).apiClient;
  } catch {
    named = undefined;
  }
  if (typeof named === 'function') {
    return named as CallableFn;
  }
  if (typeof rawDefaultApiClient === 'function') {
    return rawDefaultApiClient as CallableFn;
  }
  if (isObjectWithGet(named)) {
    return named;
  }
  if (isObjectWithGet(rawDefaultApiClient)) {
    return rawDefaultApiClient;
  }
  return null;
}

function loadMyPermissions(): Promise<MyPermissions> {
  if (!cached) {
    const client = getApiClient();
    let callPromise: Promise<MyPermissions> | null = null;
    try {
      if (typeof client === 'function') {
        callPromise = client('/api/auth/me/permissions/');
      } else if (isObjectWithGet(client)) {
        callPromise = client.get('/api/auth/me/permissions/');
      }
    } catch {
      callPromise = null;
    }

    if (callPromise && typeof callPromise.catch === 'function') {
      cached = callPromise.catch((err) => {
        cached = null;
        throw err;
      });
    } else {
      return Promise.resolve({ is_superuser: false, permissions: [] });
    }
  }
  return cached;
}

if (typeof window !== 'undefined') {
  window.addEventListener('tlbm_auth_changed', () => {
    cached = null;
  });
}

export function resetPermissionsCache(): void {
  cached = null;
}

export function hasPermission(me: MyPermissions | null, codename: string): boolean {
  return !!me && (Boolean(me.is_superuser) || (Array.isArray(me.permissions) && me.permissions.includes(codename)));
}

export function usePermissions() {
  const [me, setMe] = useState<MyPermissions | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let ignore = false;
    loadMyPermissions()
      .then((data) => {
        if (!ignore) {
          setMe(data);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (!ignore) {
          setMe(null);
          setLoaded(true);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  return {
    loaded,
    isSuperuser: Boolean(me?.is_superuser),
    can: (codename: string) => hasPermission(me, codename),
  };
}
