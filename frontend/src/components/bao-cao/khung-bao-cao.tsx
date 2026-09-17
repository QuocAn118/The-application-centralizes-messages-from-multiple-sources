"use client";

/**
 * Khung chung cho 4 màn báo cáo: chọn khoảng ngày + (chỉ Admin) chọn phòng, rồi
 * hiện nội dung bảng do màn con truyền vào.
 *
 * Ô chọn phòng **chỉ hiện cho Admin** (`chiAdminLocPhong`): Manager bị backend
 * ép về phòng mình, một ô chọn cho họ sẽ nói dối (RB-1 spec). Dùng
 * `<input type="date">` native, không thư viện.
 */

import { useState } from "react";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { chiAdminLocPhong } from "@/lib/quyen-bao-cao";
import type { KhoangNgay } from "@/lib/bao-cao-api";
import { useTenMap } from "./use-ten-map";

const LOP_O =
  "rounded-lg border border-border-subtle bg-white px-3 py-1.5 text-sm text-foreground outline-none transition focus:border-primary";

/** "YYYY-MM-DD" của một ngày (giờ địa phương). */
function iso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const ng = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${ng}`;
}

/** Mặc định: 30 ngày gần nhất, `den` = hôm nay. */
function macDinh(): KhoangNgay {
  const den = new Date();
  const tu = new Date();
  tu.setDate(tu.getDate() - 29);
  return { tu: iso(tu), den: iso(den) };
}

export interface ThamSoBaoCao {
  khoang: KhoangNgay;
  phong: string;
}

export function KhungBaoCao({
  children,
}: {
  /** Màn con nhận tham số hiện thời (khoảng + phòng) và tự truy vấn. */
  children: (thamSo: ThamSoBaoCao) => React.ReactNode;
}) {
  const { user } = useAuth();
  const [khoang, setKhoang] = useState<KhoangNgay>(macDinh);
  const [phong, setPhong] = useState("");
  const tenMap = useTenMap();

  const chonPhong = user ? chiAdminLocPhong(user.role) : false;
  // Chặn from>to ngay ở FE (đỡ một vòng mạng); backend cũng chặn (RB-3 spec).
  const khoangSai = khoang.tu > khoang.den;

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          {t("baoCao.tuNgay")}
          <input
            type="date"
            value={khoang.tu}
            max={khoang.den}
            onChange={(e) => setKhoang((k) => ({ ...k, tu: e.target.value }))}
            className={LOP_O}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-muted">
          {t("baoCao.denNgay")}
          <input
            type="date"
            value={khoang.den}
            min={khoang.tu}
            onChange={(e) => setKhoang((k) => ({ ...k, den: e.target.value }))}
            className={LOP_O}
          />
        </label>

        {chonPhong && (
          <label className="flex flex-col gap-1 text-xs font-medium text-muted">
            {t("baoCao.phong")}
            <select
              value={phong}
              onChange={(e) => setPhong(e.target.value)}
              className={LOP_O}
            >
              <option value="">{t("baoCao.moiPhong")}</option>
              {[...tenMap.phong.entries()].map(([id, ten]) => (
                <option key={id} value={id}>
                  {ten}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {khoangSai ? (
        <p className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger-fg">
          {t("baoCao.khoangSai")}
        </p>
      ) : (
        children({ khoang, phong })
      )}
    </div>
  );
}
