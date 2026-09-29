"use client";

/**
 * Tạo / sửa mẫu ca (#F3 task 2.1).
 *
 * **RB-4: giờ kết thúc PHẢI sau giờ bắt đầu.** Backend không cho ca qua nửa
 * đêm (`shift.py`: "ca không qua nửa đêm ở #4") và trả 422
 * `INVALID_SHIFT_WINDOW`. Chặn ở đây kèm câu giải thích, thay vì để người dùng
 * bấm Lưu rồi mới biết.
 *
 * Khi sửa, `PATCH /shifts/{id}` đòi **cả ba trường** (`UpdateShiftRequest`
 * không có default) — khác PATCH từng phần của `/users`. `suaCa` luôn gửi đủ.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khungGioHopLe } from "@/lib/hien-thi";
import { khoaNhanSu, suaCa, taoCa } from "@/lib/nhan-su-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import type { Department, Shift } from "@/lib/types";

export function HopThoaiCa({
  ca,
  phongBan,
  phongMacDinh,
  onDong,
}: {
  /** `null` = tạo mới. */
  ca: Shift | null;
  /** Phòng được phép chọn. Manager chỉ có một; Admin có tất cả. */
  phongBan: Department[];
  phongMacDinh: string;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const dangSua = ca !== null;

  const [ten, setTen] = useState(ca?.name ?? "");
  const [batDau, setBatDau] = useState(ca?.start_time.slice(0, 5) ?? "08:00");
  const [ketThuc, setKetThuc] = useState(ca?.end_time.slice(0, 5) ?? "17:00");
  const [phongId, setPhongId] = useState(ca?.department_id ?? phongMacDinh);

  const gioHopLe = batDau !== "" && ketThuc !== "" && khungGioHopLe(batDau, ketThuc);
  const saiGio = batDau !== "" && ketThuc !== "" && !gioHopLe;
  const hopLe = ten.trim().length > 0 && gioHopLe && phongId !== "";

  const luu = useMutation({
    mutationFn: () => {
      const chung = { name: ten.trim(), start_time: batDau, end_time: ketThuc };
      return ca
        ? suaCa(ca.id, chung)
        : taoCa({ ...chung, department_id: phongId });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.ca.all });
      // Giờ của buổi đã xếp được chụp lúc phân nên không đổi theo, nhưng TÊN ca
      // hiện trên lịch lấy từ mẫu — làm mới luôn để lịch không hiện tên cũ.
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.phanCa.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={dangSua ? t("ca.suaTieuDe") : t("ca.taoMoi")}
      moTa={dangSua ? ca.name : undefined}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => luu.mutate()} disabled={!hopLe || luu.isPending}>
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Truong nhan={t("ca.ten")} batBuoc>
          {(o) => <ONhap {...o} value={ten} onChange={(e) => setTen(e.target.value)} maxLength={200} />}
        </Truong>

        {/* Phòng ban KHÔNG sửa được: `UpdateShiftRequest` không nhận trường
            này. Khi sửa thì hiện chỉ-đọc thay vì ô chọn. */}
        {dangSua ? (
          <dl className="rounded-nb border-2 border-line bg-sunken px-3 py-2.5">
            <dt className="text-xs font-bold uppercase tracking-wide text-ink-2">{t("ca.phongBan")}</dt>
            <dd className="mt-1 text-sm font-semibold text-ink">
              {phongBan.find((p) => p.id === ca.department_id)?.name ?? t("nguoiDung.khongPhong")}
            </dd>
          </dl>
        ) : (
          <Truong nhan={t("ca.phongBan")}>
            {(o) => (
              <OChon {...o} value={phongId} onChange={(e) => setPhongId(e.target.value)}>
                {phongBan.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </OChon>
            )}
          </Truong>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Truong nhan={t("ca.batDau")}>
            {(o) => <ONhap {...o} type="time" value={batDau} onChange={(e) => setBatDau(e.target.value)} />}
          </Truong>
          {/* RB-4: lỗi nằm dưới ô Kết thúc — đó là ô người dùng cần sửa. */}
          <Truong nhan={t("ca.ketThuc")} loi={saiGio ? t("ca.gioKetThucPhaiSau") : null}>
            {(o) => <ONhap {...o} type="time" value={ketThuc} onChange={(e) => setKetThuc(e.target.value)} />}
          </Truong>
        </div>
      </div>
    </HopThoai>
  );
}
