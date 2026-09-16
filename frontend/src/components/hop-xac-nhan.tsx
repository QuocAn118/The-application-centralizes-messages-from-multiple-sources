"use client";

/**
 * Hộp xác nhận cho thao tác khó hoàn tác (#F2 task 1.3).
 *
 * Chữ trên nút do nơi gọi truyền vào, không cố định "Xoá"/"OK": ở #F2 gần như
 * không có thao tác nào là xoá thật (backend chỉ có `deactivate`), gọi nhầm tên
 * sẽ khiến người dùng tưởng mất dữ liệu — RB-5.
 */

import { HopThoai, NutChinh, NutPhu } from "./hop-thoai";
import { t } from "@/lib/i18n";

export function HopXacNhan({
  tieuDe,
  moTa,
  nhanXacNhan,
  nguyHiem = false,
  dangChay,
  loi,
  onDong,
  onXacNhan,
}: {
  tieuDe: string;
  moTa: string;
  nhanXacNhan: string;
  nguyHiem?: boolean;
  dangChay: boolean;
  loi: string | null;
  onDong: () => void;
  onXacNhan: () => void;
}) {
  return (
    <HopThoai
      tieuDe={tieuDe}
      moTa={moTa}
      loi={loi}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={dangChay}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh nguyHiem={nguyHiem} onClick={onXacNhan} disabled={dangChay}>
            {dangChay ? t("nguoiDung.dangLuu") : nhanXacNhan}
          </NutChinh>
        </>
      }
    />
  );
}
