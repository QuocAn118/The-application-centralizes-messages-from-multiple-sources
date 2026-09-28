"use client";

/**
 * Màn Kênh (#F2 GĐ3) — chỉ Admin.
 *
 * `GET /channels` trả **mảng trần**, không phải `PageResponse` như
 * `/departments` — đã đối chiếu `openapi.json`. Không phân trang, số kênh thực
 * tế rất nhỏ.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Radio } from "lucide-react";
import { t } from "@/lib/i18n";
import {
  khoaQuanTri,
  layDanhSachKenh,
  layDanhSachPhongBan,
  ngatKenh,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { BangKenh, type ThaoTacKenh } from "./bang-kenh";
import { HopThoaiKenh } from "./hop-thoai-kenh";
import type { Channel } from "@/lib/types";

type DangMo = { loai: "ketNoi" } | { loai: ThaoTacKenh; kenh: Channel } | null;

export function ManKenh() {
  const queryClient = useQueryClient();
  const [tuKhoa, setTuKhoa] = useState("");
  // Q2: mặc định chỉ kênh đang kết nối; kênh đã ngắt bật lên khi cần.
  const [hienDaNgat, setHienDaNgat] = useState(false);
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const truyVanKenh = useQuery({
    queryKey: khoaQuanTri.kenh.all,
    // Không truyền `is_active`: màn quản trị phải thấy cả kênh đã ngắt.
    queryFn: ({ signal }) => layDanhSachKenh(undefined, signal),
  });

  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  const ngat = useMutation({
    mutationFn: (kenhId: string) => ngatKenh(kenhId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.kenh.all });
      setDangMo(null);
    },
  });

  const phongBan = truyVanPhongBan.data?.items ?? [];

  const soDaNgat = (truyVanKenh.data ?? []).filter((k) => !k.is_active).length;

  const danhSach = useMemo(() => {
    const items = (truyVanKenh.data ?? []).filter((k) => hienDaNgat || k.is_active);
    const tu = tuKhoa.trim().toLowerCase();
    if (!tu) return items;
    return items.filter(
      (k) =>
        k.name.toLowerCase().includes(tu) ||
        k.external_channel_id.toLowerCase().includes(tu),
    );
  }, [truyVanKenh.data, tuKhoa, hienDaNgat]);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("kenh.tieuDe")}
        moTa="Tài khoản Telegram, Zalo, Facebook, Instagram mà hệ thống nhận tin về. Token chỉ ghi vào, không bao giờ hiện lại."
        hanhDong={
          <Nut bienThe="chinh" icon={Plus} onClick={() => setDangMo({ loai: "ketNoi" })}>
            {t("kenh.ketNoi")}
          </Nut>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <OTimKiem nhanGoiY={t("kenh.timKiem")} doiTuKhoa={setTuKhoa} />
        {soDaNgat > 0 && (
          <Nut
            co="sm"
            bienThe={hienDaNgat ? "chinh" : "phu"}
            aria-pressed={hienDaNgat}
            onClick={() => setHienDaNgat((v) => !v)}
          >
            Hiện cả kênh đã ngắt ({soDaNgat})
          </Nut>
        )}
      </div>

      {truyVanKenh.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVanKenh.isError && (
        <The>
          <TrangThaiLoi thongDiep={thongDiepLoi(truyVanKenh.error)} onThuLai={() => void truyVanKenh.refetch()} />
        </The>
      )}
      {truyVanKenh.data && danhSach.length === 0 && (
        <The>
          <TrangThaiRong icon={Radio} tieuDe={t("quanTri.trong")} />
        </The>
      )}
      {danhSach.length > 0 && (
        <BangKenh
          danhSach={danhSach}
          phongBan={phongBan}
          chonThaoTac={(thaoTac, kenh) => setDangMo({ loai: thaoTac, kenh })}
        />
      )}

      {dangMo?.loai === "ketNoi" && (
        <HopThoaiKenh kenh={null} phongBan={phongBan} onDong={() => setDangMo(null)} />
      )}
      {dangMo?.loai === "sua" && (
        <HopThoaiKenh
          kenh={dangMo.kenh}
          phongBan={phongBan}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "ngat" && (
        <HopXacNhan
          tieuDe={t("kenh.ngat")}
          moTa={t("kenh.xacNhanNgat", { ten: dangMo.kenh.name })}
          nhanXacNhan={t("kenh.ngat")}
          nguyHiem
          dangChay={ngat.isPending}
          loi={ngat.isError ? thongDiepLoi(ngat.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => ngat.mutate(dangMo.kenh.id)}
        />
      )}
    </div>
  );
}
