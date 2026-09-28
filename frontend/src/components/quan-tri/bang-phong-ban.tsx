"use client";

/**
 * Bảng phòng ban (#F2 task 2.1; redesign Phần 6 Q2).
 *
 * Số nhân viên mỗi phòng là một truy vấn riêng cho từng dòng (`GET /users` đọc
 * `total`) vì `DepartmentResponse` không mang sẵn con số đó. Với vài chục phòng
 * thì chấp nhận được; nếu sau này danh sách phòng dài ra thì nên xin backend
 * trả kèm `member_count` thay vì bắn N lời gọi.
 *
 * Thao tác qua menu "⋯" (mẫu chuẩn Q1). Phòng đã ngừng KHÔNG có mục "Ngừng hoạt
 * động": backend không có endpoint kích hoạt lại, đây là thao tác một chiều.
 */

import { useQuery } from "@tanstack/react-query";
import { Pencil, Ban } from "lucide-react";
import { t } from "@/lib/i18n";
import { demNhanVienCuaPhong, khoaQuanTri } from "@/lib/quan-tri-api";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
import type { Department } from "@/lib/types";

/** Thao tác chọn từ menu của một dòng. */
export type ThaoTacPhong = "sua" | "ngung";

export function BangPhongBan({
  danhSach,
  laAdmin,
  chonThaoTac,
}: {
  danhSach: Department[];
  laAdmin: boolean;
  chonThaoTac: (thaoTac: ThaoTacPhong, phong: Department) => void;
}) {
  return (
    <Bang aria-label={t("phongBan.tieuDe")}>
      <thead>
        <tr>
          <Th>{t("phongBan.cotTen")}</Th>
          <Th className="w-36">{t("phongBan.cotSoNhanVien")}</Th>
          <Th className="w-44">{t("phongBan.cotTrangThai")}</Th>
          <Th className="w-16">
            <span className="sr-only">{t("nguoiDung.thaoTac")}</span>
          </Th>
        </tr>
      </thead>
      <tbody>
        {danhSach.map((phong) => (
          <Tr key={phong.id} className={phong.is_active ? "" : "bg-sunken"}>
            <Td>
              <span className="block font-bold text-ink">{phong.name}</span>
              <span className="block truncate text-xs text-ink-2">
                {phong.description?.trim() || t("phongBan.khongMoTa")}
              </span>
            </Td>
            <Td>
              <SoNhanVien departmentId={phong.id} />
            </Td>
            <Td>
              <HuyHieu tong={phong.is_active ? "ok" : "trung"}>
                {/* "Ngừng hoạt động" như nút (RB-5), không dùng "vô hiệu hoá" của người dùng. */}
                {phong.is_active ? t("phongBan.dangHoatDong") : t("phongBan.trangThaiDaNgung")}
              </HuyHieu>
            </Td>
            <Td className="text-right">
              {laAdmin && (
                <MenuHanhDong
                  nhan={`${t("nguoiDung.moThaoTac")}: ${phong.name}`}
                  muc={[
                    { nhan: t("phongBan.sua"), icon: Pencil, onChon: () => chonThaoTac("sua", phong) },
                    {
                      nhan: t("phongBan.ngungHoatDong"),
                      icon: Ban,
                      nguyHiem: true,
                      an: !phong.is_active,
                      onChon: () => chonThaoTac("ngung", phong),
                    },
                  ]}
                />
              )}
            </Td>
          </Tr>
        ))}
      </tbody>
    </Bang>
  );
}

/** Số nhân viên đang hoạt động của một phòng. */
function SoNhanVien({ departmentId }: { departmentId: string }) {
  const { data, isPending, isError } = useQuery({
    queryKey: khoaQuanTri.phongBan.demNhanVien(departmentId),
    queryFn: ({ signal }) => demNhanVienCuaPhong(departmentId, signal),
  });

  if (isPending) {
    return <span className="text-xs text-ink-2">{t("phongBan.dangDemNhanVien")}</span>;
  }
  // Đếm hỏng không được làm vỡ cả bảng — hiện dấu gạch, phần còn lại vẫn dùng được.
  if (isError) return <span className="text-ink-2">—</span>;
  return <span className="font-semibold tabular-nums text-ink">{data}</span>;
}
