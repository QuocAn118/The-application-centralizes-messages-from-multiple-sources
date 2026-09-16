"use client";

/**
 * Hàng bộ lọc của màn Người dùng (#F2 task 1.4).
 *
 * Bộ lọc phòng ban **ẩn với Manager** (RB-2): backend ghi đè `department_id`
 * về phòng của chính họ, nên để bộ lọc ở đó sẽ trông như nó không ăn.
 */

import { t } from "@/lib/i18n";
import { NHAN_VAI } from "@/lib/hien-thi";
import { hienBoLocPhongBan } from "@/lib/quyen-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import type { Department, Role, ThamSoNguoiDung } from "@/lib/types";

const LOP_SELECT =
  "rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

export function BoLocNguoiDung({
  vai,
  thamSo,
  phongBan,
  doiThamSo,
}: {
  vai: Role;
  thamSo: ThamSoNguoiDung;
  phongBan: Department[];
  /** Nhận phần thay đổi; nơi gọi tự đưa `offset` về 0. */
  doiThamSo: (phan: Partial<ThamSoNguoiDung>) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border-subtle px-4 py-3">
      <OTimKiem
        giaTriDau={thamSo.search ?? ""}
        nhanGoiY={t("nguoiDung.timKiem")}
        doiTuKhoa={(tuKhoa) => doiThamSo({ search: tuKhoa || undefined })}
      />

      <select
        aria-label={t("nguoiDung.locVaiTro")}
        value={thamSo.role ?? ""}
        onChange={(e) =>
          doiThamSo({ role: (e.target.value || undefined) as Role | undefined })
        }
        className={LOP_SELECT}
      >
        <option value="">
          {t("nguoiDung.locVaiTro")}: {t("quanTri.tatCa")}
        </option>
        {(["STAFF", "MANAGER", "ADMIN"] as const).map((r) => (
          <option key={r} value={r}>
            {NHAN_VAI[r]}
          </option>
        ))}
      </select>

      {hienBoLocPhongBan(vai) && (
        <select
          aria-label={t("nguoiDung.locPhongBan")}
          value={thamSo.department_id ?? ""}
          onChange={(e) => doiThamSo({ department_id: e.target.value || undefined })}
          className={LOP_SELECT}
        >
          <option value="">
            {t("nguoiDung.locPhongBan")}: {t("quanTri.tatCa")}
          </option>
          {phongBan.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
              {p.is_active ? "" : ` (${t("phongBan.daNgung")})`}
            </option>
          ))}
        </select>
      )}

      <select
        aria-label={t("nguoiDung.locTrangThai")}
        value={thamSo.is_active === undefined ? "" : String(thamSo.is_active)}
        onChange={(e) =>
          doiThamSo({
            // Chuỗi rỗng = không lọc; "false" phải thành `false`, không phải
            // `undefined` — đây đúng chỗ dễ nuốt mất bộ lọc "đã vô hiệu hoá".
            is_active: e.target.value === "" ? undefined : e.target.value === "true",
          })
        }
        className={LOP_SELECT}
      >
        <option value="">
          {t("nguoiDung.locTrangThai")}: {t("quanTri.tatCa")}
        </option>
        <option value="true">{t("nguoiDung.dangHoatDong")}</option>
        <option value="false">{t("nguoiDung.daVoHieuHoa")}</option>
      </select>
    </div>
  );
}
