"use client";

/**
 * Màn đăng nhập (spec §4.1, mockup Stitch "Đăng nhập - OmniChat").
 *
 * Không có "Đăng ký" hay "Quên mật khẩu": tài khoản do Admin cấp (module #4).
 */

import { useEffect, useState } from "react";
import { t } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login, user, isLoading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [matKhau, setMatKhau] = useState("");
  const [hienMatKhau, setHienMatKhau] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, setDangGui] = useState(false);

  // Đã đăng nhập rồi thì không ở lại màn này.
  useEffect(() => {
    if (!isLoading && user) router.replace("/inbox");
  }, [isLoading, user, router]);

  async function xuLyGui(e: React.FormEvent) {
    e.preventDefault();
    setLoi(null);
    setDangGui(true);
    try {
      const me = await login(email, matKhau);
      // Mật khẩu tạm: bắt đổi trước khi vào việc.
      router.replace(me.must_change_password ? "/doi-mat-khau" : "/inbox");
    } catch (err) {
      setLoi(err instanceof Error ? err.message : t("dangNhap.loiChung"));
      setDangGui(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-[420px] rounded-lg border border-border-subtle bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-primary">{t("dangNhap.tieuDe")}</h1>
        <p className="mt-1 text-sm text-muted">
          {t("dangNhap.phuDe")}
        </p>

        <form onSubmit={xuLyGui} className="mt-8 space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("dangNhap.email")}
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ten@congty.vn"
              className="w-full rounded-lg border border-border-subtle px-3.5 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div>
            <label
              htmlFor="mat-khau"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {t("dangNhap.matKhau")}
            </label>
            <div className="relative">
              <input
                id="mat-khau"
                type={hienMatKhau ? "text" : "password"}
                required
                autoComplete="current-password"
                value={matKhau}
                onChange={(e) => setMatKhau(e.target.value)}
                className="w-full rounded-lg border border-border-subtle px-3.5 py-2.5 pr-11 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="button"
                onClick={() => setHienMatKhau((v) => !v)}
                aria-label={hienMatKhau ? t("dangNhap.anMatKhau") : t("dangNhap.hienMatKhau")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-soft transition hover:text-muted"
              >
                {hienMatKhau ? <IconMatDong /> : <IconMat />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={dangGui}
            className="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {dangGui ? t("dangNhap.dangGui") : t("dangNhap.nut")}
          </button>

          {loi && (
            <p
              role="alert"
              className="rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2.5 text-sm text-danger-fg"
            >
              {loi}
            </p>
          )}
        </form>
      </div>
    </main>
  );
}

function IconMat() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function IconMatDong() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-6.5 0-10-8-10-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 8 10 8a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="m1 1 22 22" />
    </svg>
  );
}
