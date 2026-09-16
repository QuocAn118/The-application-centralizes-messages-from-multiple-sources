"use client";

/**
 * Vô hiệu hoá / kích hoạt lại người dùng (#F2 task 1.7).
 *
 * Không đoán trước lỗi "Admin hoạt động cuối cùng" ở FE — FE không biết còn
 * bao nhiêu Admin đang hoạt động. Backend trả
 * `LAST_ADMIN_CANNOT_BE_DEACTIVATED` kèm thông điệp tiếng Việt và hộp xác nhận
 * hiện thẳng câu đó (RB-4). Tương tự `INACTIVE_DEPARTMENT` khi kích hoạt lại
 * người thuộc phòng đã ngừng.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import {
  khoaQuanTri,
  kichHoatLaiNguoiDung,
  voHieuHoaNguoiDung,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import type { UserResponse } from "@/lib/types";

export function HopXacNhanTrangThai({
  nguoi,
  voHieuHoa,
  onDong,
}: {
  nguoi: UserResponse;
  voHieuHoa: boolean;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();

  const chay = useMutation({
    mutationFn: () =>
      voHieuHoa ? voHieuHoaNguoiDung(nguoi.id) : kichHoatLaiNguoiDung(nguoi.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.nguoiDung.all });
      onDong();
    },
  });

  return (
    <HopXacNhan
      tieuDe={voHieuHoa ? t("nguoiDung.voHieuHoa") : t("nguoiDung.kichHoatLai")}
      moTa={
        voHieuHoa
          ? t("nguoiDung.xacNhanVoHieu", { ten: nguoi.full_name })
          : t("nguoiDung.xacNhanKichHoat", { ten: nguoi.full_name })
      }
      nhanXacNhan={voHieuHoa ? t("nguoiDung.voHieuHoa") : t("nguoiDung.kichHoatLai")}
      nguyHiem={voHieuHoa}
      dangChay={chay.isPending}
      loi={chay.isError ? thongDiepLoi(chay.error) : null}
      onDong={onDong}
      onXacNhan={() => chay.mutate()}
    />
  );
}
