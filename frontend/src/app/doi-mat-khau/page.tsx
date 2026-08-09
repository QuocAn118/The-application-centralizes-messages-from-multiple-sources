"use client";

/**
 * Đổi mật khẩu — bắt buộc với người vừa được Admin cấp mật khẩu tạm
 * (`must_change_password`, spec §6).
 *
 * Không nằm dưới `/inbox` nên không bị `AuthGuard` của nhóm đó bọc; tự kiểm tra
 * phiên ở đây. Backend cố ý cho phép gọi endpoint này kể cả khi chưa đổi mật
 * khẩu — nếu chặn thì người dùng sẽ mắc kẹt.
 */

import { useEffect, useState } from "react";
import { t } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function DoiMatKhauPage() {
  const { user, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [matKhauHienTai, setMatKhauHienTai] = useState("");
  const [matKhauMoi, setMatKhauMoi] = useState("");
  const [xacNhan, setXacNhan] = useState("");
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, setDangGui] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  async function xuLyGui(e: React.FormEvent) {
    e.preventDefault();
    setLoi(null);

    if (matKhauMoi !== xacNhan) {
      setLoi(t("doiMatKhau.khongKhop"));
      return;
    }
    if (matKhauMoi.length < 8) {
      setLoi(t("doiMatKhau.quaNgan"));
      return;
    }

    setDangGui(true);
    try {
      await api.post("/auth/change-password", {
        current_password: matKhauHienTai,
        new_password: matKhauMoi,
      });
      // Đọc lại `/auth/me` để cờ `must_change_password` về false.
      await refreshUser();
      router.replace("/inbox");
    } catch (err) {
      setLoi(
        err instanceof ApiError ? err.message : t("doiMatKhau.loiChung"),
      );
      setDangGui(false);
    }
  }

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <p className="text-sm text-muted">{t("chung.dangTai")}</p>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-[420px] rounded-lg border border-border-subtle bg-white p-8 shadow-sm">
        <h1 className="text-xl font-bold text-foreground">{t("doiMatKhau.tieuDe")}</h1>
        <p className="mt-1 text-sm text-muted">
          {user.must_change_password
            ? t("doiMatKhau.batBuoc")
            : t("doiMatKhau.tuNguyen")}
        </p>

        <form onSubmit={xuLyGui} className="mt-8 space-y-5">
          <O
            id="mk-hien-tai"
            nhan={t("doiMatKhau.hienTai")}
            giaTri={matKhauHienTai}
            doiGiaTri={setMatKhauHienTai}
            autoComplete="current-password"
          />
          <O
            id="mk-moi"
            nhan={t("doiMatKhau.moi")}
            giaTri={matKhauMoi}
            doiGiaTri={setMatKhauMoi}
            autoComplete="new-password"
            goiY={t("doiMatKhau.goiYDoDai")}
          />
          <O
            id="mk-xac-nhan"
            nhan={t("doiMatKhau.nhapLai")}
            giaTri={xacNhan}
            doiGiaTri={setXacNhan}
            autoComplete="new-password"
          />

          <button
            type="submit"
            disabled={dangGui}
            className="w-full rounded-lg bg-primary py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {dangGui ? t("doiMatKhau.dangLuu") : t("doiMatKhau.nut")}
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

function O({
  id,
  nhan,
  giaTri,
  doiGiaTri,
  autoComplete,
  goiY,
}: {
  id: string;
  nhan: string;
  giaTri: string;
  doiGiaTri: (v: string) => void;
  autoComplete: string;
  goiY?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-foreground">
        {nhan}
      </label>
      <input
        id={id}
        type="password"
        required
        autoComplete={autoComplete}
        value={giaTri}
        onChange={(e) => doiGiaTri(e.target.value)}
        className="w-full rounded-lg border border-border-subtle px-3.5 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
      {goiY && <p className="mt-1 text-xs text-muted-soft">{goiY}</p>}
    </div>
  );
}
