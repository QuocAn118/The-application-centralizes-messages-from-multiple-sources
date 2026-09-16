"use client";

/**
 * Bảng danh sách người dùng (#F2 task 1.4, mockup Stitch "Người dùng").
 *
 * Hai chỗ chỉnh so với mockup, đều vì mockup dựng trên dữ liệu giả:
 * - Badge trạng thái phải `whitespace-nowrap`: "Đang hoạt động" dài hơn ô hẹp
 *   nên trong mockup nó vỡ làm hai dòng.
 * - Dòng đã vô hiệu hoá phải mờ đi thấy rõ. Mockup chỉ đổi badge, mà khi bảng
 *   dài thì nhìn lướt không phân biệt được ai còn làm việc.
 */

import { useEffect, useRef, useState } from "react";
import { t } from "@/lib/i18n";
import { LOP_BADGE_VAI, NHAN_VAI, chuCaiDau } from "@/lib/hien-thi";
import {
  hienDatLaiMatKhau,
  hienDoiPhongBan,
  hienDoiVaiTro,
  hienSuaHoSo,
  hienVoHieuHoa,
  type NguoiThaoTac,
} from "@/lib/quyen-quan-tri";
import type { Department, UserResponse } from "@/lib/types";

/** Thao tác người dùng chọn từ menu ba chấm. */
export type ThaoTac =
  | "suaHoSo"
  | "doiVaiTro"
  | "doiPhongBan"
  | "datLaiMatKhau"
  | "voHieuHoa"
  | "kichHoatLai";

export function BangNguoiDung({
  danhSach,
  phongBan,
  actor,
  chonThaoTac,
}: {
  danhSach: UserResponse[];
  phongBan: Department[];
  actor: NguoiThaoTac;
  chonThaoTac: (thaoTac: ThaoTac, nguoi: UserResponse) => void;
}) {
  const tenPhong = new Map(phongBan.map((p) => [p.id, p.name]));

  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="border-b border-border-subtle bg-surface/60 text-[11px] font-bold uppercase tracking-wider text-muted">
          <th scope="col" className="px-5 py-3.5">{t("nguoiDung.cotNguoiDung")}</th>
          <th scope="col" className="w-36 px-4 py-3.5">{t("nguoiDung.cotVaiTro")}</th>
          <th scope="col" className="w-48 px-4 py-3.5">{t("nguoiDung.cotPhongBan")}</th>
          <th scope="col" className="w-40 px-4 py-3.5">{t("nguoiDung.cotTrangThai")}</th>
          <th scope="col" className="w-20 px-5 py-3.5 text-right">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((nguoi) => (
          <tr
            key={nguoi.id}
            className={`border-b border-border-subtle last:border-0 ${
              nguoi.is_active ? "" : "bg-surface/40 opacity-60"
            }`}
          >
            <td className="px-5 py-3">
              <div className="flex items-center gap-3">
                <span
                  aria-hidden
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary"
                >
                  {chuCaiDau(nguoi.full_name)}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-foreground">
                    {nguoi.full_name}
                    {nguoi.id === actor.id && (
                      <span className="ml-1 font-normal text-muted-soft">
                        {t("nguoiDung.chinhBan")}
                      </span>
                    )}
                  </span>
                  <span className="block truncate text-xs text-muted">{nguoi.email}</span>
                </span>
              </div>
            </td>

            <td className="px-4 py-3">
              <span
                className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${LOP_BADGE_VAI[nguoi.role]}`}
              >
                {NHAN_VAI[nguoi.role]}
              </span>
            </td>

            <td className="px-4 py-3 text-sm text-foreground">
              {nguoi.department_id
                ? (tenPhong.get(nguoi.department_id) ?? t("nguoiDung.khongPhong"))
                : t("nguoiDung.khongPhong")}
            </td>

            <td className="px-4 py-3">
              <span
                className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${
                  nguoi.is_active
                    ? "bg-dang-mo-bg text-dang-mo-fg"
                    : "bg-da-dong-bg text-da-dong-fg"
                }`}
              >
                <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
                {nguoi.is_active
                  ? t("nguoiDung.dangHoatDong")
                  : t("nguoiDung.daVoHieuHoa")}
              </span>
            </td>

            <td className="px-5 py-3 text-right">
              <MenuThaoTac
                nguoi={nguoi}
                actor={actor}
                chonThaoTac={(thaoTac) => chonThaoTac(thaoTac, nguoi)}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/**
 * Menu ba chấm. Mỗi mục hiện theo đúng quy tắc quyền đọc từ use case backend
 * (`quyen-quan-tri.ts`) — nhưng ẩn nút chỉ là UX, server vẫn là trọng tài.
 */
function MenuThaoTac({
  nguoi,
  actor,
  chonThaoTac,
}: {
  nguoi: UserResponse;
  actor: NguoiThaoTac;
  chonThaoTac: (thaoTac: ThaoTac) => void;
}) {
  const [mo, setMo] = useState(false);
  const boc = useRef<HTMLDivElement>(null);

  // Bấm ra ngoài hoặc Esc thì đóng — menu mở lơ lửng sau khi chuyển chỗ khác
  // là lỗi kinh điển của menu tự dựng.
  useEffect(() => {
    if (!mo) return;
    function bamNgoai(e: MouseEvent) {
      if (boc.current && !boc.current.contains(e.target as Node)) setMo(false);
    }
    function phim(e: KeyboardEvent) {
      if (e.key === "Escape") setMo(false);
    }
    document.addEventListener("mousedown", bamNgoai);
    document.addEventListener("keydown", phim);
    return () => {
      document.removeEventListener("mousedown", bamNgoai);
      document.removeEventListener("keydown", phim);
    };
  }, [mo]);

  const muc: { thaoTac: ThaoTac; nhan: string; nguyHiem?: boolean }[] = [];
  if (hienSuaHoSo(actor, nguoi)) {
    muc.push({ thaoTac: "suaHoSo", nhan: t("nguoiDung.suaHoSo") });
  }
  if (hienDoiVaiTro(actor)) {
    muc.push({ thaoTac: "doiVaiTro", nhan: t("nguoiDung.doiVaiTro") });
  }
  if (hienDoiPhongBan(actor)) {
    muc.push({ thaoTac: "doiPhongBan", nhan: t("nguoiDung.doiPhongBan") });
  }
  if (hienDatLaiMatKhau(actor, nguoi)) {
    muc.push({ thaoTac: "datLaiMatKhau", nhan: t("nguoiDung.datLaiMatKhau") });
  }
  if (hienVoHieuHoa(actor, nguoi)) {
    muc.push(
      nguoi.is_active
        ? { thaoTac: "voHieuHoa", nhan: t("nguoiDung.voHieuHoa"), nguyHiem: true }
        : { thaoTac: "kichHoatLai", nhan: t("nguoiDung.kichHoatLai") },
    );
  }

  // Không có thao tác nào thì không hiện nút — nút mở ra menu rỗng gây bực.
  if (muc.length === 0) return null;

  return (
    <div ref={boc} className="relative inline-block text-left">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={mo}
        aria-label={t("nguoiDung.moThaoTac")}
        onClick={() => setMo((truoc) => !truoc)}
        className="rounded-lg px-2 py-1 text-muted-soft transition hover:bg-surface hover:text-muted"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <circle cx="12" cy="5" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="19" r="2" />
        </svg>
      </button>

      {mo && (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-1 w-48 overflow-hidden rounded-lg border border-border-subtle bg-white py-1 shadow-lg"
        >
          {muc.map((m) => (
            <button
              key={m.thaoTac}
              type="button"
              role="menuitem"
              onClick={() => {
                setMo(false);
                chonThaoTac(m.thaoTac);
              }}
              className={`block w-full px-4 py-2 text-left text-sm transition hover:bg-surface ${
                m.nguyHiem ? "text-danger-fg" : "text-foreground"
              }`}
            >
              {m.nhan}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
