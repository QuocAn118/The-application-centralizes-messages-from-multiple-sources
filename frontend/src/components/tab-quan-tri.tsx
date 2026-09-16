"use client";

/**
 * Thanh tab của khu quản trị: Người dùng · Phòng ban · Kênh · Nhật ký.
 *
 * Manager chỉ thấy tab "Người dùng" — ba màn còn lại chỉ Admin (spec §2). Ẩn
 * hẳn tab thay vì hiện rồi chặn khi bấm: thấy tab mà vào không được thì trông
 * như hỏng.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { t, type KhoaChuoi } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { chiAdmin } from "@/lib/quyen-quan-tri";

interface Tab {
  duongDan: string;
  nhan: KhoaChuoi;
  /** true = chỉ Admin thấy. */
  riengAdmin: boolean;
}

// Cả bốn route đã dựng xong (GĐ1–4) nên prefetch để nguyên mặc định. Trong lúc
// GĐ2–4 còn dở, ba tab dưới phải đặt `prefetch={false}`: Next prefetch mọi
// `<Link>` trong tầm nhìn nên tab trỏ tới route chưa có sẽ bắn 404 vào console
// ngay khi mở màn. Nhớ lại điều này nếu sau có thêm tab chưa dựng.
const TAB: Tab[] = [
  { duongDan: "/quan-tri/nguoi-dung", nhan: "quanTri.tabNguoiDung", riengAdmin: false },
  { duongDan: "/quan-tri/phong-ban", nhan: "quanTri.tabPhongBan", riengAdmin: true },
  { duongDan: "/quan-tri/kenh", nhan: "quanTri.tabKenh", riengAdmin: true },
  { duongDan: "/quan-tri/nhat-ky", nhan: "quanTri.tabNhatKy", riengAdmin: true },
];

export function TabQuanTri() {
  const pathname = usePathname();
  const { user } = useAuth();
  if (!user) return null;

  const laAdmin = chiAdmin(user.role);
  const tabThay = TAB.filter((tab) => laAdmin || !tab.riengAdmin);

  return (
    <header className="shrink-0 border-b border-border-subtle bg-white px-6 pt-5">
      <h1 className="text-lg font-semibold text-foreground">{t("quanTri.tieuDe")}</h1>
      <nav className="mt-4 flex gap-1" aria-label={t("quanTri.tieuDe")}>
        {tabThay.map((tab) => {
          const dangO = pathname.startsWith(tab.duongDan);
          return (
            <Link
              key={tab.duongDan}
              href={tab.duongDan}
              aria-current={dangO ? "page" : undefined}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
                dangO
                  ? "border-primary text-primary"
                  : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {t(tab.nhan)}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
