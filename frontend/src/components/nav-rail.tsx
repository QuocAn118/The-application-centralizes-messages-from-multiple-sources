"use client";

/**
 * Thanh điều hướng dọc bên trái (mockup Stitch).
 *
 * Ba mục "Nhân sự" / "Báo cáo" / "Cấu hình" cố ý để dạng chưa dùng được: chúng
 * thuộc các sub-project FE sau (#4, #5, #2 — nợ spec §9c). Giữ chỗ sẵn để khi
 * làm tới không phải dựng lại khung.
 */

import Link from "next/link";
import { t } from "@/lib/i18n";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function NavRail() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const dangOInbox = pathname.startsWith("/inbox");

  const chuCaiDau = user?.full_name?.trim()?.[0]?.toUpperCase() ?? "?";

  return (
    <nav className="flex w-[72px] shrink-0 flex-col items-center gap-1 border-r border-border-subtle bg-white py-4">
      <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
        OC
      </div>

      <Link
        href="/inbox"
        aria-current={dangOInbox ? "page" : undefined}
        className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition ${
          dangOInbox
            ? "bg-primary-soft text-primary"
            : "text-muted-soft hover:bg-surface"
        }`}
      >
        <IconHopThu />
        {t("nav.hopThu")}
      </Link>

      {[
        { nhan: t("nav.nhanSu"), icon: <IconNhanSu /> },
        { nhan: t("nav.baoCao"), icon: <IconBaoCao /> },
        { nhan: t("nav.cauHinh"), icon: <IconCauHinh /> },
      ].map((muc) => (
        <span
          key={muc.nhan}
          title={t("nav.sauNay")}
          aria-disabled="true"
          className="flex w-14 cursor-not-allowed flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium text-muted-soft/50"
        >
          {muc.icon}
          {muc.nhan}
        </span>
      ))}

      <div className="mt-auto flex flex-col items-center gap-2">
        <div
          title={user ? `${user.full_name} (${user.role})` : undefined}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-surface text-sm font-semibold text-muted"
        >
          {chuCaiDau}
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="text-[10px] text-muted-soft transition hover:text-danger-fg"
        >
          {t("nav.dangXuat")}
        </button>
      </div>
    </nav>
  );
}

function IconHopThu() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16v12H7l-3 3V4Z" />
    </svg>
  );
}

function IconNhanSu() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0M16 11a3 3 0 1 0 0-6M18 20a5 5 0 0 0-3-4.58" />
    </svg>
  );
}

function IconBaoCao() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </svg>
  );
}

function IconCauHinh() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15H4.5a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 6 9.4l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 11 4.6V4.5a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 2.82 1.17l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 11h.1a2 2 0 1 1 0 4h-.1Z" />
    </svg>
  );
}
