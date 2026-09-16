"use client";

/**
 * Thanh điều hướng dọc bên trái (mockup Stitch).
 *
 * "Báo cáo" còn để dạng chưa dùng được — thuộc #F5.
 *
 * Ba mục đã mở khác nhau ở chỗ ai vào được:
 * - "Nhân sự" (#F3): **mọi vai**, Staff cũng xem ca và gửi đơn được.
 * - "Từ khoá" (#F4): **mọi vai**, Staff xem được nhưng không sửa.
 * - "Cấu hình" (#F2): chỉ Admin/Manager; Staff vẫn thấy mục khoá.
 */

import Link from "next/link";
import { t } from "@/lib/i18n";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { vaoDuocKhuQuanTri } from "@/lib/quyen-quan-tri";

export function NavRail() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const dangOInbox = pathname.startsWith("/inbox");
  const dangOQuanTri = pathname.startsWith("/quan-tri");
  const dangONhanSu = pathname.startsWith("/nhan-su");
  const dangOTuKhoa = pathname.startsWith("/tu-khoa");
  const moKhoaCauHinh = user ? vaoDuocKhuQuanTri(user.role) : false;

  const chuCaiDau = user?.full_name?.trim()?.[0]?.toUpperCase() ?? "?";

  return (
    <nav className="flex w-[72px] shrink-0 flex-col items-center gap-1 border-r border-border-subtle bg-white py-4">
      <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
        OC
      </div>

      <Link
        href="/inbox"
        aria-current={dangOInbox ? "true" : undefined}
        className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition ${
          dangOInbox
            ? "bg-primary-soft text-primary"
            : "text-muted-soft hover:bg-surface"
        }`}
      >
        <IconHopThu />
        {t("nav.hopThu")}
      </Link>

      <Link
        href="/nhan-su/don-tu"
        aria-current={dangONhanSu ? "true" : undefined}
        className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition ${
          dangONhanSu
            ? "bg-primary-soft text-primary"
            : "text-muted-soft hover:bg-surface"
        }`}
      >
        <IconNhanSu />
        {t("nav.nhanSu")}
      </Link>

      <Link
        href="/tu-khoa/danh-sach"
        aria-current={dangOTuKhoa ? "true" : undefined}
        className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition ${
          dangOTuKhoa
            ? "bg-primary-soft text-primary"
            : "text-muted-soft hover:bg-surface"
        }`}
      >
        <IconTuKhoa />
        {t("nav.tuKhoa")}
      </Link>

      <span
        title={t("nav.sauNay")}
        aria-disabled="true"
        className="flex w-14 cursor-not-allowed flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium text-muted-soft/50"
      >
        <IconBaoCao />
        {t("nav.baoCao")}
      </span>

      {moKhoaCauHinh ? (
        <Link
          href="/quan-tri/nguoi-dung"
          // `"true"` chứ không phải `"page"`: mục này chỉ ra KHU VỰC đang mở,
          // còn trang cụ thể do thanh tab bên trong đánh dấu. Để cả hai cùng
          // `"page"` thì trình đọc màn hình báo hai "trang hiện tại".
          aria-current={dangOQuanTri ? "true" : undefined}
          className={`flex w-14 flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium transition ${
            dangOQuanTri
              ? "bg-primary-soft text-primary"
              : "text-muted-soft hover:bg-surface"
          }`}
        >
          <IconCauHinh />
          {t("nav.cauHinh")}
        </Link>
      ) : (
        <span
          title={t("nav.khongDuQuyen")}
          aria-disabled="true"
          className="flex w-14 cursor-not-allowed flex-col items-center gap-1 rounded-lg py-2 text-[10px] font-medium text-muted-soft/50"
        >
          <IconCauHinh />
          {t("nav.cauHinh")}
        </span>
      )}

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

function IconTuKhoa() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20.6 13.4 12 22l-9-9V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z" />
      <circle cx="7.5" cy="7.5" r="1.5" />
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
