"use client";

/**
 * Màn Phòng ban (#F2 GĐ2) — chỉ Admin.
 *
 * Danh sách phòng ban ngắn (vài chục) nên lấy trần 100 và lọc/tìm ngay tại
 * client, không phân trang: đi vòng qua server cho mỗi lần gõ chỉ tốn thêm độ
 * trễ mà không được gì.
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaQuanTri, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import { BangPhongBan, type ThaoTacPhong } from "./bang-phong-ban";
import { HopThoaiPhongBan } from "./hop-thoai-phong-ban";
import { HopXacNhanNgungPhong } from "./hop-xac-nhan-ngung-phong";
import type { Department } from "@/lib/types";

type DangMo =
  | { loai: "tao" }
  | { loai: ThaoTacPhong; phong: Department }
  | null;

export function ManPhongBan() {
  const [tuKhoa, setTuKhoa] = useState("");
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const truyVan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  const danhSach = useMemo(() => {
    const items = truyVan.data?.items ?? [];
    const tu = tuKhoa.trim().toLowerCase();
    if (!tu) return items;
    return items.filter(
      (p) =>
        p.name.toLowerCase().includes(tu) ||
        (p.description ?? "").toLowerCase().includes(tu),
    );
  }, [truyVan.data, tuKhoa]);

  return (
    <div className="px-6 py-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-foreground">
          {t("phongBan.tieuDe")}
        </h2>
        <button
          type="button"
          onClick={() => setDangMo({ loai: "tao" })}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
        >
          + {t("phongBan.taoMoi")}
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="border-b border-border-subtle px-4 py-3">
          <OTimKiem nhanGoiY={t("phongBan.timKiem")} doiTuKhoa={setTuKhoa} />
        </div>

        {truyVan.isPending && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("chung.dangTai")}
          </p>
        )}

        {truyVan.isError && (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-danger-fg">{thongDiepLoi(truyVan.error)}</p>
            <button
              type="button"
              onClick={() => void truyVan.refetch()}
              className="mt-3 rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("chung.thuLai")}
            </button>
          </div>
        )}

        {truyVan.data && danhSach.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("quanTri.trong")}
          </p>
        )}

        {danhSach.length > 0 && (
          <BangPhongBan
            danhSach={danhSach}
            laAdmin
            chonThaoTac={(thaoTac, phong) => setDangMo({ loai: thaoTac, phong })}
          />
        )}
      </div>

      {dangMo?.loai === "tao" && (
        <HopThoaiPhongBan phong={null} onDong={() => setDangMo(null)} />
      )}
      {dangMo?.loai === "sua" && (
        <HopThoaiPhongBan phong={dangMo.phong} onDong={() => setDangMo(null)} />
      )}
      {dangMo?.loai === "ngung" && (
        <HopXacNhanNgungPhong phong={dangMo.phong} onDong={() => setDangMo(null)} />
      )}
    </div>
  );
}
