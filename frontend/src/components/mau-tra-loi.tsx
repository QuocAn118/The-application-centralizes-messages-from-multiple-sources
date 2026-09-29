"use client";

/**
 * Mẫu trả lời nhanh (BE-7, GĐ1 I11): danh sách chọn nổi trên ô soạn + hộp quản lý
 * cho Manager/Admin. Không đụng luồng gửi — chọn mẫu chỉ chèn chữ vào ô soạn.
 *
 * Danh sách là một `listbox` điều khiển từ ô soạn (combobox): focus vẫn ở ô soạn,
 * ↑↓ đổi mục đang chọn qua `aria-activedescendant`, Enter chọn, Esc đóng.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  khoaMau,
  khoaPhongBan,
  layMau,
  layPhongBanHoatDong,
  suaMau,
  taoMau,
  xoaMau,
} from "@/lib/inbox-api";
import type { ReplyTemplate } from "@/lib/types";
import { NutChinh, NutPhu } from "./hop-thoai";
import { KhungQuanLy } from "./khung-quan-ly";
import { HuyHieu } from "./ui/huy-hieu";
import { Nut } from "./ui/nut";
import { NutIcon } from "./ui/nut-icon";
import { OChon, ONhap, VungNhap } from "./ui/o-nhap";

export const ID_DANH_SACH_MAU = "danh-sach-mau-tra-loi";
export const idMucMau = (i: number) => `mau-tra-loi-${i}`;

export function useMau() {
  return useQuery({ queryKey: khoaMau, queryFn: ({ signal }) => layMau(signal), staleTime: 60_000 });
}

export function DanhSachMau({
  mau,
  chiSo,
  dangTai,
  onChon,
  onQuanLy,
}: {
  mau: ReplyTemplate[];
  chiSo: number;
  dangTai: boolean;
  onChon: (m: ReplyTemplate) => void;
  onQuanLy?: () => void;
}) {
  return (
    <div className="absolute bottom-full left-4 right-4 z-30 mb-2 rounded-nb border-2 border-ink bg-card shadow-nb">
      <div className="flex items-center justify-between border-b-2 border-ink px-3 py-2">
        <p className="text-xs font-bold uppercase tracking-wide text-ink-2">
          Mẫu trả lời · ↑↓ chọn · Enter chèn · Esc đóng
        </p>
        {onQuanLy && (
          <Nut bienThe="trong" co="sm" onMouseDown={(e) => e.preventDefault()} onClick={onQuanLy}>
            Quản lý mẫu
          </Nut>
        )}
      </div>
      <ul id={ID_DANH_SACH_MAU} role="listbox" aria-label="Mẫu trả lời" className="max-h-64 overflow-y-auto p-1">
        {dangTai && <li className="px-3 py-2 text-sm text-ink-2">Đang tải…</li>}
        {!dangTai && mau.length === 0 && (
          <li className="px-3 py-2 text-sm text-ink-2">Không có mẫu nào khớp.</li>
        )}
        {mau.map((m, i) => (
          <li
            key={m.id}
            id={idMucMau(i)}
            role="option"
            aria-selected={i === chiSo}
            // Giữ focus ở ô soạn khi bấm chuột.
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onChon(m)}
            className={`cursor-pointer rounded-[4px] px-3 py-2 ${i === chiSo ? "bg-accent" : "hover:bg-sunken"}`}
          >
            <span className="flex items-center gap-2 text-sm font-bold text-ink">
              {m.title}
              {m.department_id === null && <HuyHieu>Dùng chung</HuyHieu>}
            </span>
            <span className="mt-0.5 block truncate text-xs text-ink-2">{m.body}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const loiCua = (e: unknown) => (e instanceof ApiError ? e.message : "Không thực hiện được. Thử lại.");

/** Quản lý mẫu: hộp thoại trong Hộp thư (`onDong`) hoặc tab Cấu hình (`trang`). */
export function HopQuanLyMau({ onDong, trang = false }: { onDong?: () => void; trang?: boolean }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const laAdmin = user?.role === "ADMIN";
  const { data: mau = [] } = useMau();
  const { data: phong } = useQuery({
    queryKey: khoaPhongBan,
    queryFn: ({ signal }) => layPhongBanHoatDong(signal),
    enabled: laAdmin,
  });
  const tenPhong = (id: string | null) =>
    id === null ? "Dùng chung" : (phong?.items.find((p) => p.id === id)?.name ?? "Phòng mình");

  // `null` = đang tạo mới; một mẫu = đang sửa mẫu đó.
  const [dangSua, setDangSua] = useState<ReplyTemplate | null>(null);
  const [tieuDe, setTieuDe] = useState("");
  const [noiDung, setNoiDung] = useState("");
  const [phamVi, setPhamVi] = useState<string>(laAdmin ? "" : (user?.department_id ?? ""));
  const [loi, setLoi] = useState<string | null>(null);
  // Xoá cần bấm hai lần: lần đầu đổi nút thành "Xoá hẳn?" (thao tác huỷ hoại phải xác nhận).
  const [choXoa, setChoXoa] = useState<string | null>(null);

  const suaDuoc = (m: ReplyTemplate) =>
    laAdmin || (user?.role === "MANAGER" && m.department_id === user.department_id);

  function datLai() {
    setDangSua(null);
    setTieuDe("");
    setNoiDung("");
    setLoi(null);
  }
  const xong = () => {
    datLai();
    setChoXoa(null);
    void qc.invalidateQueries({ queryKey: khoaMau });
  };

  const luu = useMutation({
    mutationFn: () =>
      dangSua
        ? suaMau(dangSua.id, { title: tieuDe, body: noiDung })
        : taoMau({ department_id: phamVi || null, title: tieuDe, body: noiDung }),
    onSuccess: xong,
    onError: (e) => setLoi(loiCua(e)),
  });
  const xoa = useMutation({
    mutationFn: (id: string) => xoaMau(id),
    onSuccess: xong,
    onError: (e) => setLoi(loiCua(e)),
  });

  return (
    <KhungQuanLy
      trang={trang}
      tieuDe={trang ? "Mẫu trả lời" : "Quản lý mẫu trả lời"}
      moTa={
        laAdmin
          ? "Mẫu dùng chung hiện cho mọi phòng; mẫu của phòng chỉ phòng đó thấy."
          : "Bạn quản lý mẫu của phòng mình. Mẫu dùng chung do quản trị viên quản lý."
      }
      loi={loi}
      onDong={onDong}
    >
      <form
        className="flex flex-col gap-3 rounded-nb border-2 border-ink bg-sunken p-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (tieuDe.trim() && noiDung.trim()) luu.mutate();
        }}
      >
        <p className="text-sm font-bold text-ink">{dangSua ? `Sửa "${dangSua.title}"` : "Mẫu mới"}</p>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          Tiêu đề
          <ONhap value={tieuDe} maxLength={80} onChange={(e) => setTieuDe(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          Nội dung
          <VungNhap value={noiDung} maxLength={4000} onChange={(e) => setNoiDung(e.target.value)} />
        </label>
        {laAdmin && !dangSua && (
          <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
            Ai thấy mẫu này
            <OChon value={phamVi} onChange={(e) => setPhamVi(e.target.value)}>
              <option value="">Dùng chung mọi phòng</option>
              {phong?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </OChon>
          </label>
        )}
        <div className="flex gap-2">
          <NutChinh type="submit" disabled={!tieuDe.trim() || !noiDung.trim() || luu.isPending}>
            {dangSua ? "Lưu thay đổi" : (
              <>
                <Plus aria-hidden className="size-4" /> Tạo mẫu
              </>
            )}
          </NutChinh>
          {dangSua && <NutPhu onClick={datLai}>Huỷ sửa</NutPhu>}
        </div>
      </form>

      {mau.length === 0 && <p className="mt-4 text-sm text-ink-2">Chưa có mẫu nào. Tạo mẫu đầu tiên ở trên.</p>}
      <ul className="mt-4 flex flex-col divide-y-2 divide-line">
        {mau.map((m) => (
          <li key={m.id} className="flex items-start gap-2 py-2">
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-sm font-bold text-ink">
                {m.title}
                <HuyHieu>{tenPhong(m.department_id)}</HuyHieu>
              </p>
              <p className="truncate text-xs text-ink-2">{m.body}</p>
            </div>
            {suaDuoc(m) && (
              <>
                <NutIcon
                  icon={Pencil}
                  nhan={`Sửa mẫu ${m.title}`}
                  co="sm"
                  onClick={() => {
                    setDangSua(m);
                    setTieuDe(m.title);
                    setNoiDung(m.body);
                  }}
                />
                {choXoa === m.id ? (
                  <>
                    <Nut bienThe="nguyHiem" co="sm" dangChay={xoa.isPending} onClick={() => xoa.mutate(m.id)}>
                      Xoá hẳn?
                    </Nut>
                    <Nut bienThe="trong" co="sm" onClick={() => setChoXoa(null)}>
                      Thôi
                    </Nut>
                  </>
                ) : (
                  <NutIcon
                    icon={Trash2}
                    nhan={`Xoá mẫu ${m.title}`}
                    co="sm"
                    onClick={() => setChoXoa(m.id)}
                  />
                )}
              </>
            )}
          </li>
        ))}
      </ul>
    </KhungQuanLy>
  );
}
