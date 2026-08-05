"use client";

/**
 * Context xác thực: giữ người đang đăng nhập và access token.
 *
 * Access token chỉ sống trong bộ nhớ (spec §7) nên tải lại trang là mất. Bù
 * lại, khi khởi động ta thử `/api/session/refresh` một lần: cookie httpOnly còn
 * hạn thì phiên được khôi phục mà người dùng không phải đăng nhập lại.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  api,
  setAccessToken,
  setOnSessionExpired,
  getAccessToken,
} from "./api-client";
import type { UserResponse } from "./types";

interface AuthState {
  user: UserResponse | null;
  /** `true` trong lúc khôi phục phiên lúc khởi động — chưa biết đã đăng nhập chưa. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<UserResponse>;
  logout: () => Promise<void>;
  /** Đọc lại `/auth/me`, dùng sau khi đổi mật khẩu. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/** Thân trả về từ Route Handler — cố ý không có `refresh_token`. */
interface SessionPayload {
  access_token: string;
  token_type: string;
  expires_in: number;
  must_change_password: boolean;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Giữ trong ref để hàm dọn dẹp không phụ thuộc giá trị state cũ.
  const daHuy = useRef(false);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  /**
   * Khôi phục phiên khi tải trang.
   *
   * Chạy đúng một lần: nếu cookie hết hạn thì kết luận "chưa đăng nhập" và để
   * guard đưa về `/login`, không thử lại vòng lặp.
   */
  useEffect(() => {
    daHuy.current = false;

    (async () => {
      try {
        const res = await fetch("/api/session/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) throw new Error("no-session");

        const data = (await res.json()) as SessionPayload;
        setAccessToken(data.access_token);

        const me = await api.get<UserResponse>("/auth/me");
        if (!daHuy.current) setUser(me);
      } catch {
        if (!daHuy.current) clearSession();
      } finally {
        if (!daHuy.current) setIsLoading(false);
      }
    })();

    return () => {
      daHuy.current = true;
    };
  }, [clearSession]);

  /**
   * Khi tầng API client kết luận phiên đã chết, dọn state và đẩy về `/login`.
   * Nối ở đây vì api-client cố ý không biết gì về React hay router.
   */
  useEffect(() => {
    setOnSessionExpired(() => {
      clearSession();
      router.replace("/login");
    });
    return () => setOnSessionExpired(null);
  }, [clearSession, router]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch("/api/session/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const message =
        body?.error?.message ?? "Email hoặc mật khẩu không đúng.";
      throw new Error(message);
    }

    const data = (await res.json()) as SessionPayload;
    setAccessToken(data.access_token);

    const me = await api.get<UserResponse>("/auth/me");
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    const token = getAccessToken();
    try {
      await fetch("/api/session/logout", {
        method: "POST",
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
    } finally {
      // Dọn phía client dù server có lỗi — người dùng đã yêu cầu đăng xuất.
      clearSession();
      router.replace("/login");
    }
  }, [clearSession, router]);

  const refreshUser = useCallback(async () => {
    const me = await api.get<UserResponse>("/auth/me");
    setUser(me);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, logout, refreshUser }),
    [user, isLoading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth phải được dùng bên trong <AuthProvider>.");
  }
  return ctx;
}
