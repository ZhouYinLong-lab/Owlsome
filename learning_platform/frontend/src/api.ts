export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

// ── Admin token helpers ─────────────────────────────────────────────

const ADMIN_TOKEN_KEY = "owlsome.adminToken";

export function readAdminToken(): string | null {
  return localStorage.getItem(ADMIN_TOKEN_KEY);
}

export function writeAdminToken(token: string): void {
  localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function adminHeaders(): Record<string, string> {
  const token = readAdminToken();
  if (token) return { "X-Admin-Token": token };
  return {};
}

/** Like api() but automatically attaches the admin token header.
 *  If the server returns 403, the error message suggests checking the admin token. */
export async function adminApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...adminHeaders(),
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 403) {
      throw new Error("管理员 token 无效或未配置，请重新切换管理员模式并填写正确 token。");
    }
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}
