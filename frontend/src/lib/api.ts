// JWT fetch 封裝：自動帶 Authorization，統一錯誤型別。
import i18n from "../i18n";

const TOKEN_KEY = "scholaragent.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface Options {
  method?: string;
  body?: unknown;
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(path, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) detail = i18n.t("common.invalidInput");
    } catch {
      // 非 JSON 回應就用 statusText
    }
    // token 失效（過期、改過密碼、已登出所有裝置）：清掉並回登入頁
    if (resp.status === 401 && token && !path.startsWith("/auth/")) {
      setToken(null);
      window.location.hash = "#/login";
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

/** 以登入身分下載檔案（瀏覽器直接開連結不會帶 Authorization）。 */
export async function download(path: string, filename: string): Promise<void> {
  const token = getToken();
  const resp = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!resp.ok) throw new ApiError(resp.status, i18n.t("common.downloadFailed"));
  const url = URL.createObjectURL(await resp.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  locale: string;
  has_password: boolean;
  google: boolean;
  github: boolean;
  discord: boolean;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}
