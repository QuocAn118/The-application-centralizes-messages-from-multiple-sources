"use client";

/**
 * Bảng danh sách người dùng (#F2 task 1.4; redesign Phần 6 Q1).
 *
 * Menu "⋯" ở đây là MẪU CHUẨN cho thao tác trên dòng (GĐ1 Q1) — nay chạy trên
 * `MenuHanhDong` (Radix) như mọi màn khác, bỏ bản menu tự viết tay.
 *
 * Dòng đã vô hiệu hoá: nền lõm + huy hiệu "Đã vô hiệu hoá", KHÔNG làm mờ bằng
 * `opacity` như trước — chữ mờ trượt tương phản mà vẫn phải đọc được tên.
 */

import { KeyRound, Pencil, ShieldCheck, Building2, UserX, UserCheck } from "lucide-react";
import { t } from "@/lib/i18n";
import { LOP_BADGE_VAI, NHAN_VAI } from "@/lib/hien-thi";
import {
  hienDatLaiMatKhau,
  hienDoiPhongBan,
  hienDoiVaiTro,
  hienSuaHoSo,
  hienVoHieuHoa,
  type NguoiThaoTac,
} from "@/lib/quyen-quan-tri";
import { Avatar } from "@/components/ui/avatar";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
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
    <Bang aria-label={t("nguoiDung.tieuDe")}>
      <thead>
        <tr>
          <Th>{t("nguoiDung.cotNguoiDung")}</Th>
          <Th className="w-36">{t("nguoiDung.cotVaiTro")}</Th>
          <Th className="w-52">{t("nguoiDung.cotPhongBan")}</Th>
          <Th className="w-44">{t("nguoiDung.cotTrangThai")}</Th>
          <Th className="w-16">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((nguoi) => (
          <Tr key={nguoi.id} className={nguoi.is_active ? "" : "bg-sunken"}>
            <Td>
              <div className="flex items-center gap-3">
                <Avatar id={nguoi.id} ten={nguoi.full_name} co="sm" />
                <span className="min-w-0">
                  <span className="block truncate font-bold text-ink">
                    {nguoi.full_name}
                    {nguoi.id === actor.id && (
                      <span className="ml-1 font-semibold text-ink-2">{t("nguoiDung.chinhBan")}</span>
                    )}
                  </span>
                  <span className="block truncate text-xs text-ink-2">{nguoi.email}</span>
                </span>
              </div>
            </Td>
            <Td>
              <HuyHieu lop={LOP_BADGE_VAI[nguoi.role]}>{NHAN_VAI[nguoi.role]}</HuyHieu>
            </Td>
            <Td>
              {nguoi.department_id
                ? (tenPhong.get(nguoi.department_id) ?? t("nguoiDung.khongPhong"))
                : <span className="text-ink-2">{t("nguoiDung.khongPhong")}</span>}
            </Td>
            <Td>
              <HuyHieu tong={nguoi.is_active ? "ok" : "trung"}>
                {nguoi.is_active ? t("nguoiDung.dangHoatDong") : t("nguoiDung.daVoHieuHoa")}
              </HuyHieu>
            </Td>
            <Td className="text-right">
              {/* Mỗi mục hiện theo đúng quy tắc quyền đọc từ use case backend
                  (`quyen-quan-tri.ts`) — ẩn mục chỉ là UX, server vẫn là trọng tài.
                  Không có mục nào thì MenuHanhDong tự không vẽ nút. */}
              <MenuHanhDong
                nhan={t("nguoiDung.moThaoTac")}
                muc={[
                  { nhan: t("nguoiDung.suaHoSo"), icon: Pencil, an: !hienSuaHoSo(actor, nguoi), onChon: () => chonThaoTac("suaHoSo", nguoi) },
                  { nhan: t("nguoiDung.doiVaiTro"), icon: ShieldCheck, an: !hienDoiVaiTro(actor), onChon: () => chonThaoTac("doiVaiTro", nguoi) },
                  { nhan: t("nguoiDung.doiPhongBan"), icon: Building2, an: !hienDoiPhongBan(actor), onChon: () => chonThaoTac("doiPhongBan", nguoi) },
                  { nhan: t("nguoiDung.datLaiMatKhau"), icon: KeyRound, an: !hienDatLaiMatKhau(actor, nguoi), onChon: () => chonThaoTac("datLaiMatKhau", nguoi) },
                  nguoi.is_active
                    ? { nhan: t("nguoiDung.voHieuHoa"), icon: UserX, nguyHiem: true, an: !hienVoHieuHoa(actor, nguoi), onChon: () => chonThaoTac("voHieuHoa", nguoi) }
                    : { nhan: t("nguoiDung.kichHoatLai"), icon: UserCheck, an: !hienVoHieuHoa(actor, nguoi), onChon: () => chonThaoTac("kichHoatLai", nguoi) },
                ]}
              />
            </Td>
          </Tr>
        ))}
      </tbody>
    </Bang>
  );
}
