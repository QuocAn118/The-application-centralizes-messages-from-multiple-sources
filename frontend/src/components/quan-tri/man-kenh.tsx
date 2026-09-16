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
import { t } from "@/lib/i18n";
import {
  khoaQuanTri,
  layDanhSachKenh,
  layDanhSachPhongBan,
  ngatKenh,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { OTimKiem } from "@/components/o-tim-kiem";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { BangKenh, type ThaoTacKenh } from "./bang-kenh";
import { HopThoaiKenh } from "./hop-thoai-kenh";
import type { Channel } from "@/lib/types";

type DangMo = { loai: "ketNoi" } | { loai: ThaoTacKenh; kenh: Channel } | null;

export function ManKenh() {
  const queryClient = useQueryClient();
  const [tuKhoa, setTuKhoa] = useState("");
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

  const danhSach = useMemo(() => {
    const items = truyVanKenh.data ?? [];
    const tu = tuKhoa.trim().toLowerCase();
    if (!tu) return items;
    return items.filter(
      (k) =>
        k.name.toLowerCase().includes(tu) ||
        k.external_channel_id.toLowerCase().includes(tu),
    );
  }, [truyVanKenh.data, tuKhoa]);

  return (
    <div className="px-6 py-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-foreground">{t("kenh.tieuDe")}</h2>
        <button
          type="button"
          onClick={() => setDangMo({ loai: "ketNoi" })}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
        >
          + {t("kenh.ketNoi")}
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="border-b border-border-subtle px-4 py-3">
          <OTimKiem nhanGoiY={t("kenh.timKiem")} doiTuKhoa={setTuKhoa} />
        </div>

        {truyVanKenh.isPending && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("chung.dangTai")}
          </p>
        )}

        {truyVanKenh.isError && (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-danger-fg">{thongDiepLoi(truyVanKenh.error)}</p>
            <button
              type="button"
              onClick={() => void truyVanKenh.refetch()}
              className="mt-3 rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("chung.thuLai")}
            </button>
          </div>
        )}

        {truyVanKenh.data && danhSach.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("quanTri.trong")}
          </p>
        )}

        {danhSach.length > 0 && (
          <BangKenh
            danhSach={danhSach}
            phongBan={phongBan}
            chonThaoTac={(thaoTac, kenh) => setDangMo({ loai: thaoTac, kenh })}
          />
        )}
      </div>

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
