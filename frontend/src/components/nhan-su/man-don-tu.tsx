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
import { FileText, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { NHAN_LOAI_DON, NHAN_TRANG_THAI_DON } from "@/lib/hien-thi";
import { hienSoChuaDoc } from "@/lib/hop-thu";
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
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import type { LeaveRequest, RequestStatus } from "@/lib/types";

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
  // D1: Manager/Admin mở ra ở "Chờ duyệt" — việc cần làm, không lẫn đơn đã quyết.
  const [thamSo, setThamSo] = useState<ThamSoDon>(() => ({
    limit: KICH_THUOC_TRANG_DON,
    offset: 0,
    status: user && user.role !== "STAFF" ? "CHO_DUYET" : undefined,
  }));
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

  // Số trên nút "Chờ duyệt": chỉ cần `total`, nên xin 1 dòng.
  const truyVanDemCho = useQuery({
    queryKey: [...khoaNhanSu.don.all, "dem-cho"],
    queryFn: ({ signal }) =>
      layDanhSachDon({ status: "CHO_DUYET", limit: 1, offset: 0 }, signal),
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

  const soCho = hienSoChuaDoc(truyVanDemCho.data?.total ?? 0);
  const locTheo = (status: RequestStatus | undefined) =>
    setThamSo((truoc) => ({ ...truoc, status, offset: 0 }));

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("don.tieuDe")}
        moTa={
          actor.role === "STAFF"
            ? "Đơn bạn đã gửi và kết quả duyệt."
            : "Duyệt đơn nghỉ phép, đổi ca, giải trình trong phạm vi của bạn."
        }
        hanhDong={
          hienGuiDon(actor) ? (
            <Nut bienThe="chinh" icon={Plus} onClick={() => setDangMo({ loai: "gui" })}>
              {t("don.guiDon")}
            </Nut>
          ) : (
            // D2 / RB-1: Admin không gửi đơn được vì không thuộc phòng nào — nói rõ
            // ngay chỗ lẽ ra có nút, thay vì để người dùng tự hỏi nút đâu.
            <p className="max-w-[36ch] rounded-nb border-2 border-dashed border-ink-2 px-3 py-2 text-xs text-ink-2">
              {t("don.adminKhongGuiDuoc")}
            </p>
          )
        }
      />

      <div role="group" aria-label={t("don.locTrangThai")} className="flex flex-wrap gap-2">
        {TRANG_THAI.map((tt) => (
          <Nut
            key={tt}
            co="sm"
            bienThe={thamSo.status === tt ? "chinh" : "phu"}
            aria-pressed={thamSo.status === tt}
            onClick={() => locTheo(tt)}
          >
            {NHAN_TRANG_THAI_DON[tt]}
            {tt === "CHO_DUYET" && soCho && (
              <span className="rounded-full bg-ink px-1.5 text-xs font-extrabold text-card">{soCho}</span>
            )}
          </Nut>
        ))}
        <Nut
          co="sm"
          bienThe={thamSo.status === undefined ? "chinh" : "phu"}
          aria-pressed={thamSo.status === undefined}
          onClick={() => locTheo(undefined)}
        >
          {t("quanTri.tatCa")}
        </Nut>
      </div>

      {truyVanDon.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVanDon.isError && (
        <The>
          <TrangThaiLoi
            thongDiep={thongDiepLoi(truyVanDon.error)}
            onThuLai={() => void truyVanDon.refetch()}
          />
        </The>
      )}
      {trang && trang.items.length === 0 && (
        <The>
          <TrangThaiRong
            icon={FileText}
            tieuDe={thamSo.status === "CHO_DUYET" ? "Không có đơn nào chờ duyệt" : t("quanTri.trong")}
          />
        </The>
      )}
      {trang && trang.items.length > 0 && (
        <div className="flex flex-col gap-3">
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
            doiOffset={(offsetMoi) => setThamSo((truoc) => ({ ...truoc, offset: offsetMoi }))}
          />
        </div>
      )}

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
