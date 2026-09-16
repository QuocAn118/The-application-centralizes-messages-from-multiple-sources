"use client";

/**
 * Màn Đơn từ (#F3 GĐ1).
 *
 * **Chỗ khó nhất là RB-2**: quyền duyệt phụ thuộc vai của người gửi, mà
 * `LeaveRequest` chỉ mang `requester_id`. Nên màn này tải sẵn danh sách người
 * dùng để tra ngược — vừa lấy tên hiển thị, vừa lấy vai cho `hienDuyet`.
 *
 * Tải một lần 100 người thay vì gọi `GET /users/{id}` cho từng dòng: 25 dòng là
 * 25 lời gọi, mà phần lớn trỏ tới cùng vài người.
 */

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { NHAN_LOAI_DON, NHAN_TRANG_THAI_DON } from "@/lib/hien-thi";
import {
  KICH_THUOC_TRANG_DON,
  duyetDon,
  khoaNhanSu,
  layDanhSachDon,
  thuHoiDon,
  type ThamSoDon,
} from "@/lib/nhan-su-api";
import { khoaQuanTri, layDanhSachNguoiDung } from "@/lib/quan-tri-api";
import { hienGuiDon, type NguoiNhanSu } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { BangDon, type ThaoTacDon } from "./bang-don";
import { HopThoaiGuiDon } from "./hop-thoai-gui-don";
import { HopThoaiTuChoi } from "./hop-thoai-tu-choi";
import type { LeaveRequest, RequestStatus } from "@/lib/types";

const LOP_SELECT =
  "rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition focus:border-primary";

const TRANG_THAI: readonly RequestStatus[] = [
  "CHO_DUYET",
  "DA_DUYET",
  "TU_CHOI",
  "DA_HUY",
] as const;

type DangMo = { loai: "gui" } | { loai: ThaoTacDon; don: LeaveRequest } | null;

export function ManDonTu() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [thamSo, setThamSo] = useState<ThamSoDon>({
    limit: KICH_THUOC_TRANG_DON,
    offset: 0,
  });
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const truyVanDon = useQuery({
    queryKey: [...khoaNhanSu.don.all, thamSo],
    queryFn: ({ signal }) => layDanhSachDon(thamSo, signal),
  });

  // Dùng chung khoá với #F2 để không tải lại danh sách người dùng hai lần khi
  // người dùng chuyển qua lại giữa hai khu.
  const truyVanNguoiDung = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "tra-ten"],
    queryFn: ({ signal }) => layDanhSachNguoiDung({ limit: 100, offset: 0 }, signal),
    // Staff bị chặn `GET /users` (403) — không sao: khi đó bảng tra rỗng, tên
    // hiện "Không rõ" và `hienDuyet` nhận `null`. Staff vốn không duyệt đơn
    // nên không mất gì. Không thử lại để khỏi bắn 403 liên tục.
    retry: false,
  });

  const nguoiTheoId = useMemo(
    () => new Map((truyVanNguoiDung.data?.items ?? []).map((u) => [u.id, u])),
    [truyVanNguoiDung.data],
  );

  const duyet = useMutation({
    mutationFn: (donId: string) => duyetDon(donId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.don.all });
      setDangMo(null);
    },
  });

  const thuHoi = useMutation({
    mutationFn: (donId: string) => thuHoiDon(donId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.don.all });
      setDangMo(null);
    },
  });

  if (!user) return null;

  const actor: NguoiNhanSu = {
    id: user.id,
    role: user.role,
    department_id: user.department_id,
  };
  const trang = truyVanDon.data;

  function tenNguoiGui(don: LeaveRequest): string {
    return nguoiTheoId.get(don.requester_id)?.full_name ?? t("nhatKy.khongRo");
  }

  return (
    <div className="px-6 py-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-base font-semibold text-foreground">{t("don.tieuDe")}</h2>
        {hienGuiDon(actor) ? (
          <button
            type="button"
            onClick={() => setDangMo({ loai: "gui" })}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
          >
            + {t("don.guiDon")}
          </button>
        ) : (
          // RB-1: Admin không gửi đơn được vì không thuộc phòng nào. Nói rõ lý
          // do thay vì để chỗ trống — người dùng sẽ tự hỏi nút đâu.
          <p className="text-xs text-muted">{t("don.adminKhongGuiDuoc")}</p>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border border-border-subtle bg-white">
        <div className="flex flex-wrap items-center gap-3 border-b border-border-subtle px-4 py-3">
          <select
            aria-label={t("don.locTrangThai")}
            value={thamSo.status ?? ""}
            onChange={(e) =>
              setThamSo((truoc) => ({
                ...truoc,
                status: (e.target.value || undefined) as RequestStatus | undefined,
                offset: 0,
              }))
            }
            className={LOP_SELECT}
          >
            <option value="">
              {t("don.locTrangThai")}: {t("quanTri.tatCa")}
            </option>
            {TRANG_THAI.map((tt) => (
              <option key={tt} value={tt}>
                {NHAN_TRANG_THAI_DON[tt]}
              </option>
            ))}
          </select>
        </div>

        {truyVanDon.isPending && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("chung.dangTai")}
          </p>
        )}

        {truyVanDon.isError && (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-danger-fg">{thongDiepLoi(truyVanDon.error)}</p>
            <button
              type="button"
              onClick={() => void truyVanDon.refetch()}
              className="mt-3 rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-foreground transition hover:bg-surface"
            >
              {t("chung.thuLai")}
            </button>
          </div>
        )}

        {trang && trang.items.length === 0 && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            {t("quanTri.trong")}
          </p>
        )}

        {trang && trang.items.length > 0 && (
          <>
            <BangDon
              danhSach={trang.items}
              nguoiTheoId={nguoiTheoId}
              actor={actor}
              chonThaoTac={(thaoTac, don) => setDangMo({ loai: thaoTac, don })}
            />
            <ThanhPhanTrang
              offset={trang.offset}
              limit={trang.limit}
              total={trang.total}
              dangTai={truyVanDon.isFetching}
              doiOffset={(offsetMoi) =>
                setThamSo((truoc) => ({ ...truoc, offset: offsetMoi }))
              }
            />
          </>
        )}
      </div>

      {dangMo?.loai === "gui" && <HopThoaiGuiDon onDong={() => setDangMo(null)} />}

      {dangMo?.loai === "duyet" && (
        <HopXacNhan
          tieuDe={t("don.duyet")}
          moTa={t("don.xacNhanDuyet", {
            loai: NHAN_LOAI_DON[dangMo.don.request_type].toLowerCase(),
            ten: tenNguoiGui(dangMo.don),
          })}
          nhanXacNhan={t("don.duyet")}
          dangChay={duyet.isPending}
          loi={duyet.isError ? thongDiepLoi(duyet.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => duyet.mutate(dangMo.don.id)}
        />
      )}

      {dangMo?.loai === "tuChoi" && (
        <HopThoaiTuChoi
          don={dangMo.don}
          tenNguoiGui={tenNguoiGui(dangMo.don)}
          onDong={() => setDangMo(null)}
        />
      )}

      {dangMo?.loai === "thuHoi" && (
        <HopXacNhan
          tieuDe={t("don.thuHoi")}
          moTa={t("don.xacNhanThuHoi")}
          nhanXacNhan={t("don.thuHoi")}
          nguyHiem
          dangChay={thuHoi.isPending}
          loi={thuHoi.isError ? thongDiepLoi(thuHoi.error) : null}
          onDong={() => setDangMo(null)}
          onXacNhan={() => thuHoi.mutate(dangMo.don.id)}
        />
      )}
    </div>
  );
}
