"use client";

/**
 * Ngừng hoạt động phòng ban (#F2 task 2.3, RB-5).
 *
 * Nhãn là "Ngừng hoạt động", KHÔNG phải "Xoá": backend chỉ có `deactivate`,
 * dữ liệu cũ giữ nguyên. Dùng chữ "Xoá" sẽ khiến người dùng tưởng mất dữ liệu.
 *
 * Và nói rõ **không bật lại được**: backend có `reactivate` cho người dùng
 * nhưng KHÔNG có cho phòng ban (đã đọc `department_router.py` — chỉ có
 * `deactivate`). `Department` cũng không có phương thức bật lại. Nếu chỉ nói
 * "dữ liệu vẫn còn" thì người dùng sẽ tưởng bật lại được lúc nào cũng được.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import {
  demNhanVienCuaPhong,
  khoaQuanTri,
  ngungHoatDongPhongBan,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Department } from "@/lib/types";

export function HopXacNhanNgungPhong({
  phong,
  onDong,
}: {
  phong: Department;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();

  // Hỏi trước số nhân viên: backend sẽ từ chối bằng
  // `DEPARTMENT_HAS_ACTIVE_MEMBERS` nếu phòng còn người, nên nói trước sẽ tử tế
  // hơn là để người dùng bấm rồi nhận lỗi.
  const dem = useQuery({
    queryKey: khoaQuanTri.phongBan.demNhanVien(phong.id),
    queryFn: ({ signal }) => demNhanVienCuaPhong(phong.id, signal),
  });

  const conNguoi = dem.data !== undefined && dem.data > 0;

  const ngung = useMutation({
    mutationFn: () => ngungHoatDongPhongBan(phong.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.phongBan.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={t("phongBan.ngungHoatDong")}
      moTa={t("phongBan.xacNhanNgung", { ten: phong.name })}
      loi={ngung.isError ? thongDiepLoi(ngung.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={ngung.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh
            nguyHiem
            onClick={() => ngung.mutate()}
            // Khoá nút khi biết chắc còn người, và khi chưa đếm xong — bấm
            // trong lúc chưa biết thì chỉ dẫn tới một lỗi đã đoán trước được.
            disabled={ngung.isPending || dem.isPending || conNguoi}
          >
            {ngung.isPending
              ? t("nguoiDung.dangLuu")
              : t("phongBan.ngungHoatDong")}
          </NutChinh>
        </>
      }
    >
      {conNguoi && (
        <p className="mt-4 rounded-lg border border-cho-phan-fg/30 bg-cho-phan-bg px-3.5 py-2.5 text-xs text-cho-phan-fg">
          {t("phongBan.conNhanVien", { so: dem.data })}
        </p>
      )}
    </HopThoai>
  );
}
