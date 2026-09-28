"use client";

/**
 * Bảng kênh đã kết nối (#F2 task 3.1; redesign Phần 6 Q2/Q3).
 *
 * **RB-6 — credential không bao giờ xuất hiện ở đây.** `ChannelResponse` của
 * backend cố ý không mang credential về (có ghi chú trong chính schema), nên
 * bảng này không có gì để lộ. Đừng thêm cột nào đọc token, kể cả dạng che dấu:
 * FE không có token để che.
 *
 * Q3: "Ngắt kênh" không còn là nút đỏ trên mọi dòng — vào menu "⋯", nằm cuối,
 * và vẫn qua hộp xác nhận (X5). Kênh đã ngắt không có mục này: backend không có
 * endpoint kết nối lại (chỉ `deactivate`).
 */

import { Pencil, Unplug } from "lucide-react";
import { t } from "@/lib/i18n";
import { NHAN_KENH } from "@/lib/hien-thi";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { IconKenh } from "@/components/ui/icon-kenh";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
import type { Channel, Department } from "@/lib/types";

export type ThaoTacKenh = "sua" | "ngat";

export function BangKenh({
  danhSach,
  phongBan,
  chonThaoTac,
}: {
  danhSach: Channel[];
  phongBan: Department[];
  chonThaoTac: (thaoTac: ThaoTacKenh, kenh: Channel) => void;
}) {
  const tenPhong = new Map(phongBan.map((p) => [p.id, p.name]));

  return (
    <Bang aria-label={t("kenh.tieuDe")}>
      <thead>
        <tr>
          <Th>{t("kenh.cotKenh")}</Th>
          <Th className="w-40">{t("kenh.cotNenTang")}</Th>
          <Th className="w-52">{t("kenh.cotPhongBan")}</Th>
          <Th className="w-40">{t("kenh.cotTrangThai")}</Th>
          <Th className="w-16">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((kenh) => (
          <Tr key={kenh.id} className={kenh.is_active ? "" : "bg-sunken"}>
            <Td>
              <span className="block font-bold text-ink">{kenh.name}</span>
              {/* Mã kênh trên nền tảng (OA ID / Page ID) — công khai, không
                  phải bí mật. Token mới là bí mật, và nó không có ở đây. */}
              <span className="block truncate font-mono text-xs text-ink-2">{kenh.external_channel_id}</span>
            </Td>
            <Td>
              <span className="inline-flex items-center gap-2 font-semibold">
                {/* Logo đã có tên kênh ngay cạnh → ẩn khỏi trình đọc màn hình, khỏi đọc hai lần. */}
                <span aria-hidden className="inline-flex">
                  <IconKenh kenh={kenh.platform} />
                </span>
                {NHAN_KENH[kenh.platform]}
              </span>
            </Td>
            <Td>
              {kenh.department_id ? (
                (tenPhong.get(kenh.department_id) ?? t("nguoiDung.khongPhong"))
              ) : (
                <span className="text-ink-2">{t("nguoiDung.khongPhong")}</span>
              )}
            </Td>
            <Td>
              <HuyHieu tong={kenh.is_active ? "ok" : "trung"}>
                {kenh.is_active ? t("kenh.dangKetNoi") : t("kenh.daNgat")}
              </HuyHieu>
            </Td>
            <Td className="text-right">
              <MenuHanhDong
                nhan={`${t("nguoiDung.moThaoTac")}: ${kenh.name}`}
                muc={[
                  { nhan: t("kenh.sua"), icon: Pencil, onChon: () => chonThaoTac("sua", kenh) },
                  {
                    nhan: t("kenh.ngat"),
                    icon: Unplug,
                    nguyHiem: true,
                    an: !kenh.is_active,
                    onChon: () => chonThaoTac("ngat", kenh),
                  },
                ]}
              />
            </Td>
          </Tr>
        ))}
      </tbody>
    </Bang>
  );
}
