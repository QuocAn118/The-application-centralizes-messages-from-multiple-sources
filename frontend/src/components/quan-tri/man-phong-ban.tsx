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
import { Building2, Plus } from "lucide-react";
import { t } from "@/lib/i18n";
import { khoaQuanTri, layDanhSachPhongBan } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
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
  // Q2: mặc định chỉ phòng đang hoạt động — phòng đã ngừng cùng trọng lượng
  // với phòng đang chạy làm danh sách rối.
  const [hienDaNgung, setHienDaNgung] = useState(false);
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const truyVan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  const tatCa = truyVan.data?.items ?? [];
  const soDaNgung = tatCa.filter((p) => !p.is_active).length;

  const danhSach = useMemo(() => {
    const items = (truyVan.data?.items ?? []).filter((p) => hienDaNgung || p.is_active);
    const tu = tuKhoa.trim().toLowerCase();
    if (!tu) return items;
    return items.filter(
      (p) =>
        p.name.toLowerCase().includes(tu) ||
        (p.description ?? "").toLowerCase().includes(tu),
    );
  }, [truyVan.data, tuKhoa, hienDaNgung]);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("phongBan.tieuDe")}
        moTa="Mỗi phòng nhận hội thoại của kênh mình phụ trách và có một quản lý."
        hanhDong={
          <Nut bienThe="chinh" icon={Plus} onClick={() => setDangMo({ loai: "tao" })}>
            {t("phongBan.taoMoi")}
          </Nut>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <OTimKiem nhanGoiY={t("phongBan.timKiem")} doiTuKhoa={setTuKhoa} />
        {soDaNgung > 0 && (
          <Nut
            co="sm"
            bienThe={hienDaNgung ? "chinh" : "phu"}
            aria-pressed={hienDaNgung}
            onClick={() => setHienDaNgung((v) => !v)}
          >
            Hiện cả phòng đã ngừng ({soDaNgung})
          </Nut>
        )}
      </div>

      {truyVan.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVan.isError && (
        <The>
          <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
        </The>
      )}
      {truyVan.data && danhSach.length === 0 && (
        <The>
          <TrangThaiRong icon={Building2} tieuDe={t("quanTri.trong")} />
        </The>
      )}
      {danhSach.length > 0 && (
        <BangPhongBan
          danhSach={danhSach}
          laAdmin
          chonThaoTac={(thaoTac, phong) => setDangMo({ loai: thaoTac, phong })}
        />
      )}

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
