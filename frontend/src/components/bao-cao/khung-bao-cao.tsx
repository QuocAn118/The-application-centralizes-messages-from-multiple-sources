"use client";

/**
 * Khung chung cho 4 màn báo cáo: đầu trang + chọn khoảng ngày + (chỉ Admin) chọn
 * phòng, rồi hiện nội dung do màn con truyền vào.
 *
 * Redesign Phần 5 B3: nút nhanh **7 ngày · 30 ngày · Tháng này · Tháng trước**;
 * ô ngày tuỳ chọn vẫn giữ (`<input type="date">` native, không thư viện). Nút
 * đang khớp khoảng hiện tại thì bật (`aria-pressed`).
 *
 * Ô chọn phòng **chỉ hiện cho Admin** (`chiAdminLocPhong`): Manager bị backend
 * ép về phòng mình, một ô chọn cho họ sẽ nói dối (RB-1 spec #F5).
 */

import { useState } from "react";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { chiAdminLocPhong } from "@/lib/quyen-bao-cao";
import type { KhoangNgay } from "@/lib/bao-cao-api";
import { CAC_KHOANG_NHANH, khoangNhanh, loaiKhoangDangChon } from "@/lib/khoang-bao-cao";
import { DauTrang } from "@/components/ui/dau-trang";
import { Nut } from "@/components/ui/nut";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import { useTenMap } from "./use-ten-map";

export interface ThamSoBaoCao {
  khoang: KhoangNgay;
  phong: string;
}

export function KhungBaoCao({
  tieuDe,
  moTa,
  children,
}: {
  tieuDe: string;
  moTa: string;
  /** Màn con nhận tham số hiện thời (khoảng + phòng) và tự truy vấn. */
  children: (thamSo: ThamSoBaoCao) => React.ReactNode;
}) {
  const { user } = useAuth();
  const [khoang, setKhoang] = useState<KhoangNgay>(() => khoangNhanh("30-ngay"));
  const [phong, setPhong] = useState("");
  const tenMap = useTenMap();

  const chonPhong = user ? chiAdminLocPhong(user.role) : false;
  // Chặn from>to ngay ở FE (đỡ một vòng mạng); backend cũng chặn (RB-3 spec).
  const khoangSai = khoang.tu > khoang.den;
  const dangChon = loaiKhoangDangChon(khoang);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang tieuDe={tieuDe} moTa={moTa} />

      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        <div role="group" aria-label={t("baoCao.khoangNhanh")} className="flex flex-wrap gap-2">
          {CAC_KHOANG_NHANH.map(({ loai, nhan }) => (
            <Nut
              key={loai}
              co="sm"
              bienThe={dangChon === loai ? "chinh" : "phu"}
              aria-pressed={dangChon === loai}
              onClick={() => setKhoang(khoangNhanh(loai))}
            >
              {nhan}
            </Nut>
          ))}
        </div>

        <div className="flex items-end gap-2">
          <label className="flex flex-col gap-1 text-xs font-semibold text-ink-2">
            {t("baoCao.tuNgay")}
            <ONhap
              type="date"
              value={khoang.tu}
              max={khoang.den}
              onChange={(e) => setKhoang((k) => ({ ...k, tu: e.target.value }))}
              className="w-40"
            />
          </label>
          <span aria-hidden className="pb-2.5 text-ink-2">
            –
          </span>
          <label className="flex flex-col gap-1 text-xs font-semibold text-ink-2">
            {t("baoCao.denNgay")}
            <ONhap
              type="date"
              value={khoang.den}
              min={khoang.tu}
              onChange={(e) => setKhoang((k) => ({ ...k, den: e.target.value }))}
              className="w-40"
            />
          </label>
        </div>

        {chonPhong && (
          <label className="flex flex-col gap-1 text-xs font-semibold text-ink-2">
            {t("baoCao.phong")}
            <OChon value={phong} onChange={(e) => setPhong(e.target.value)} className="w-56">
              <option value="">{t("baoCao.moiPhong")}</option>
              {[...tenMap.phong.entries()].map(([id, ten]) => (
                <option key={id} value={id}>
                  {ten}
                </option>
              ))}
            </OChon>
          </label>
        )}
      </div>

      {khoangSai ? (
        <p role="alert" className="rounded-nb border-2 border-bad bg-bad-bg px-4 py-3 text-sm font-semibold text-bad">
          {t("baoCao.khoangSai")}
        </p>
      ) : (
        children({ khoang, phong })
      )}
    </div>
  );
}
