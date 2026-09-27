"use client";

/**
 * Thanh điều hướng dọc bên trái (redesign Phần 1: lucide + Neo-Brutalism).
 *
 * Ai vào được khu nào:
 * - "Hộp thư", "Nhân sự", "Từ khoá": **mọi vai** (Staff xem được, quyền sửa do
 *   từng màn quyết).
 * - "Báo cáo", "Cấu hình": chỉ Manager/Admin. Staff vẫn THẤY mục nhưng bị khoá
 *   (biết có khu này, không bấm vào thứ chắc chắn hỏng).
 *
 * Mục đang ở: nền vàng, KHÔNG bóng (không còn là thứ để bấm). Mục khác: rê thì
 * hiện viền + bóng khi rê (quy tắc bóng: mục bấm được có bóng nhỏ + phản hồi).
 *
 * `aria-current="true"` chứ không phải `"page"`: mục này chỉ KHU VỰC đang mở;
 * trang cụ thể do thanh tab bên trong đánh dấu `"page"`. Hai chỗ cùng `"page"` thì
 * trình đọc màn hình báo hai "trang hiện tại".
 *
 * `<nav>` này cố ý KHÔNG có `aria-label`: các kịch bản kiểm chứng #F4 phân biệt
 * nó với `<nav aria-label>` của thanh tab bằng đúng điểm đó.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChartColumn,
  Lock,
  LogOut,
  MessagesSquare,
  Settings,
  Tags,
  Users,
  type LucideIcon,
} from "lucide-react";
import { t, type KhoaChuoi } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { vaoDuocKhuQuanTri } from "@/lib/quyen-quan-tri";
import { vaoDuocKhuBaoCao } from "@/lib/quyen-bao-cao";
import { NHAN_VAI } from "@/lib/hien-thi";
import type { Role } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { khoaInbox, layDemChuaDoc } from "@/lib/inbox-api";
import { hienSoChuaDoc } from "@/lib/hop-thu";
import { khoaNhanSu, layDanhSachDon } from "@/lib/nhan-su-api";
import { demDonCanDuyet } from "@/lib/quyen-nhan-su";
import { GoiY } from "./ui/goi-y";

interface MucNav {
  /** Tiền tố đường dẫn của khu — để biết đang ở khu nào. */
  khu: string;
  /** Trang mở ra khi bấm. */
  href: string;
  nhan: KhoaChuoi;
  icon: LucideIcon;
  /** Vai được vào; bỏ trống = mọi vai. */
  choPhep?: (vai: Role) => boolean;
}

const MUC: MucNav[] = [
  { khu: "/inbox", href: "/inbox", nhan: "nav.hopThu", icon: MessagesSquare },
  { khu: "/nhan-su", href: "/nhan-su/don-tu", nhan: "nav.nhanSu", icon: Users },
  { khu: "/tu-khoa", href: "/tu-khoa/danh-sach", nhan: "nav.tuKhoa", icon: Tags },
  { khu: "/bao-cao", href: "/bao-cao/hoi-thoai", nhan: "nav.baoCao", icon: ChartColumn, choPhep: vaoDuocKhuBaoCao },
  { khu: "/quan-tri", href: "/quan-tri/nguoi-dung", nhan: "nav.cauHinh", icon: Settings, choPhep: vaoDuocKhuQuanTri },
];

/**
 * Số hội thoại có tin chưa đọc (BE-1). Khoá nằm dưới `inbox` nên tín hiệu
 * realtime / đánh dấu đã đọc làm mới nó; ngoài Hộp thư thì làm mới khi quay lại tab.
 */
function HuyHieuChuaDoc() {
  const { user } = useAuth();
  const { data } = useQuery({
    queryKey: khoaInbox.chuaDoc,
    queryFn: ({ signal }) => layDemChuaDoc(signal),
    enabled: Boolean(user),
  });
  const so = hienSoChuaDoc(data?.conversations ?? 0);
  if (!so) return null;
  return <SoTrenIcon so={so} moTa={`${so} hội thoại chưa đọc`} />;
}

/**
 * Số đơn chờ mà người xem duyệt được (X14) — chỉ Manager/Admin. Khoá dưới
 * `khoaNhanSu.don.all` nên duyệt / từ chối / gửi đơn là làm mới luôn.
 */
function HuyHieuDonCho() {
  const { user } = useAuth();
  const duyetDuoc = user?.role === "MANAGER" || user?.role === "ADMIN";
  const { data } = useQuery({
    queryKey: [...khoaNhanSu.don.all, "cho-duyet-nav"],
    queryFn: ({ signal }) => layDanhSachDon({ status: "CHO_DUYET", limit: 100, offset: 0 }, signal),
    enabled: duyetDuoc,
  });
  if (!user || !duyetDuoc || !data) return null;
  const so = hienSoChuaDoc(demDonCanDuyet(user, data.items));
  if (!so) return null;
  return <SoTrenIcon so={so} moTa={`${so} đơn chờ duyệt`} />;
}

function SoTrenIcon({ so, moTa }: { so: string; moTa: string }) {
  return (
    <>
      <span
        aria-hidden
        className="absolute -right-3.5 -top-2 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full border-2 border-ink bg-bad px-1 text-xs font-extrabold leading-none text-white"
      >
        {so}
      </span>
      <span className="sr-only"> ({moTa})</span>
    </>
  );
}

const LOP_MUC =
  "flex w-16 flex-col items-center gap-1 rounded-nb border-2 py-2 text-xs font-bold leading-tight";

export function NavRail() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const chuCaiDau = user?.full_name?.trim()?.[0]?.toUpperCase() ?? "?";

  return (
    <nav className="flex w-[84px] shrink-0 flex-col items-center gap-2 border-r-2 border-ink bg-card py-4">
      <div className="mb-3 flex size-10 items-center justify-center rounded-nb border-2 border-ink bg-ink text-sm font-extrabold text-accent">
        OC
      </div>

      {MUC.map((muc) => {
        const Icon = muc.icon;
        const duocVao = user ? (muc.choPhep?.(user.role) ?? true) : false;

        if (!duocVao) {
          return (
            <GoiY key={muc.khu} noiDung={t("nav.khongDuQuyen")} phia="right">
              <span
                tabIndex={0}
                aria-disabled="true"
                className={`${LOP_MUC} relative cursor-not-allowed border-transparent text-ink-2`}
              >
                <Icon aria-hidden className="size-5" strokeWidth={2} />
                {t(muc.nhan)}
                <Lock aria-hidden className="absolute right-1.5 top-1 size-3" strokeWidth={2.5} />
              </span>
            </GoiY>
          );
        }

        const dangO = pathname.startsWith(muc.khu);
        return (
          <Link
            key={muc.khu}
            href={muc.href}
            aria-current={dangO ? "true" : undefined}
            className={`${LOP_MUC} transition-[transform,box-shadow] duration-100 ${
              dangO
                ? "border-ink bg-accent text-ink"
                : "border-transparent text-ink-2 hover:border-ink hover:text-ink hover:shadow-nb-sm"
            }`}
          >
            <span className="relative">
              <Icon aria-hidden className="size-5" strokeWidth={dangO ? 2.5 : 2} />
              {muc.khu === "/inbox" && <HuyHieuChuaDoc />}
              {muc.khu === "/nhan-su" && <HuyHieuDonCho />}
            </span>
            {t(muc.nhan)}
          </Link>
        );
      })}

      <div className="mt-auto flex flex-col items-center gap-2">
        <GoiY noiDung={user ? `${user.full_name} · ${NHAN_VAI[user.role]}` : ""} phia="right">
          <span
            tabIndex={0}
            className="flex size-10 items-center justify-center rounded-nb border-2 border-ink bg-swatch-6 text-sm font-extrabold text-ink"
          >
            {chuCaiDau}
          </span>
        </GoiY>
        <button
          type="button"
          onClick={() => void logout()}
          className={`${LOP_MUC} border-transparent text-ink-2 hover:border-bad hover:text-bad`}
        >
          <LogOut aria-hidden className="size-5" strokeWidth={2} />
          {t("nav.dangXuat")}
        </button>
      </div>
    </nav>
  );
}
