"use client";

/**
 * Ba mục panel khách của Phần 2b: Nhãn (BE-6), Ghi chú theo phòng (BE-5), Lịch sử
 * hội thoại (BE-4). Mỗi mục tự tải dữ liệu của mình — hỏng một mục không kéo cả
 * panel hỏng theo.
 */

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Settings2, Trash2, X } from "lucide-react";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { NHAN_TRANG_THAI } from "@/lib/hien-thi";
import { mocTuongDoi, nhanPhamViGhiChu } from "@/lib/hop-thu";
import {
  ganNhanKhach,
  khoaInbox,
  khoaNhan,
  khoaPhongBan,
  layGhiChu,
  layLichSuKhach,
  layNhan,
  layNhanKhach,
  layPhongBanHoatDong,
  suaNhan,
  taoNhan,
  vietGhiChu,
  xoaGhiChu,
} from "@/lib/inbox-api";
import { useBayGio } from "@/lib/use-bay-gio";
import type { CustomerNote, MauNhan, Tag } from "@/lib/types";
import { HopThoai, NutChinh, NutPhu } from "./hop-thoai";
import { HopXacNhan } from "./hop-xac-nhan";
import { lopMau, type SoMau } from "./ui/ban-mau";
import { HuyHieu } from "./ui/huy-hieu";
import { Nut } from "./ui/nut";
import { NutIcon } from "./ui/nut-icon";
import { OChon, ONhap, VungNhap } from "./ui/o-nhap";

const MAU_NHAN: MauNhan[] = Array.from({ length: 8 }, (_, i) => `swatch-${i + 1}` as MauNhan);
const lopNhan = (mau: MauNhan) => lopMau(Number(mau.split("-")[1]) as SoMau);
const loiCua = (e: unknown) => (e instanceof ApiError ? e.message : "Không thực hiện được. Thử lại.");

export function TieuDeMuc({ children, phai }: { children: React.ReactNode; phai?: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <h3 className="text-xs font-bold uppercase tracking-wide text-ink-2">{children}</h3>
      {phai}
    </div>
  );
}

// ---- Nhãn -----------------------------------------------------------------

export function MucNhan({ customerId }: { customerId: string }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const quanLy = user?.role === "MANAGER" || user?.role === "ADMIN";
  const [moQuanLy, setMoQuanLy] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);

  const { data: cuaKhach = [] } = useQuery({
    queryKey: khoaInbox.nhanKhach(customerId),
    queryFn: ({ signal }) => layNhanKhach(customerId, signal),
  });
  const { data: tatCa = [] } = useQuery({
    queryKey: khoaNhan(false),
    queryFn: ({ signal }) => layNhan(false, signal),
  });

  const gan = useMutation({
    mutationFn: (ids: string[]) => ganNhanKhach(customerId, ids),
    onSuccess: (moi) => {
      setLoi(null);
      qc.setQueryData(khoaInbox.nhanKhach(customerId), moi);
    },
    onError: (e) => setLoi(loiCua(e)),
  });

  const chuaGan = tatCa.filter((t) => !cuaKhach.some((c) => c.id === t.id));
  const idsHienTai = cuaKhach.map((t) => t.id);

  return (
    <section aria-labelledby="muc-nhan">
      <TieuDeMuc
        phai={
          quanLy && (
            <NutIcon icon={Settings2} nhan="Quản lý nhãn" co="sm" onClick={() => setMoQuanLy(true)} />
          )
        }
      >
        <span id="muc-nhan">Nhãn</span>
      </TieuDeMuc>

      {cuaKhach.length > 0 && (
        <ul className="mb-2 flex flex-wrap gap-1.5">
          {cuaKhach.map((t) => (
            <li
              key={t.id}
              className={`inline-flex items-center gap-1 rounded-nb border-2 border-ink py-0.5 pl-2 pr-0.5 text-xs font-bold text-ink ${lopNhan(t.color)}`}
            >
              {t.name}
              <button
                type="button"
                aria-label={`Gỡ nhãn ${t.name}`}
                disabled={gan.isPending}
                onClick={() => gan.mutate(idsHienTai.filter((id) => id !== t.id))}
                className="inline-flex size-5 items-center justify-center rounded-[3px] hover:bg-ink hover:text-card"
              >
                <X aria-hidden className="size-3.5" strokeWidth={3} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {chuaGan.length > 0 ? (
        <OChon
          aria-label="Gắn nhãn"
          value=""
          disabled={gan.isPending}
          onChange={(e) => e.target.value && gan.mutate([...idsHienTai, e.target.value])}
        >
          <option value="">+ Gắn nhãn…</option>
          {chuaGan.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </OChon>
      ) : (
        cuaKhach.length === 0 && (
          <p className="text-sm text-ink-2">
            {quanLy ? "Chưa có nhãn nào — tạo trong Quản lý nhãn." : "Chưa có nhãn nào để gắn."}
          </p>
        )
      )}
      {loi && (
        <p role="alert" className="mt-1 text-xs font-semibold text-bad">
          {loi}
        </p>
      )}

      {moQuanLy && <HopQuanLyNhan onDong={() => setMoQuanLy(false)} />}
    </section>
  );
}

function HopQuanLyNhan({ onDong }: { onDong: () => void }) {
  const qc = useQueryClient();
  const [ten, setTen] = useState("");
  const [mau, setMau] = useState<MauNhan>("swatch-1");
  const [loi, setLoi] = useState<string | null>(null);

  const { data: tatCa = [] } = useQuery({
    queryKey: khoaNhan(true),
    queryFn: ({ signal }) => layNhan(true, signal),
  });
  const lamMoi = () => {
    setLoi(null);
    void qc.invalidateQueries({ queryKey: ["nhan"] });
  };

  const tao = useMutation({
    mutationFn: () => taoNhan(ten, mau),
    onSuccess: () => {
      setTen("");
      lamMoi();
    },
    onError: (e) => setLoi(loiCua(e)),
  });
  const doiTrangThai = useMutation({
    mutationFn: (t: Tag) => suaNhan(t.id, { is_active: !t.is_active }),
    onSuccess: lamMoi,
    onError: (e) => setLoi(loiCua(e)),
  });

  return (
    <HopThoai
      tieuDe="Quản lý nhãn"
      moTa="Nhãn dùng chung toàn công ty. Ngừng dùng thì nhãn không gắn mới được, khách đang có vẫn giữ."
      loi={loi}
      onDong={onDong}
      chanDuoi={<NutPhu onClick={onDong}>Xong</NutPhu>}
    >
      <form
        className="flex flex-col gap-3 rounded-nb border-2 border-ink bg-sunken p-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (ten.trim()) tao.mutate();
        }}
      >
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          Tên nhãn mới
          <ONhap value={ten} maxLength={40} onChange={(e) => setTen(e.target.value)} placeholder="VD: Khách VIP" />
        </label>
        <fieldset>
          <legend className="mb-1.5 text-sm font-semibold text-ink">Màu</legend>
          <div className="flex gap-2">
            {MAU_NHAN.map((m) => (
              <label key={m} className="cursor-pointer">
                <input
                  type="radio"
                  name="mau-nhan"
                  value={m}
                  checked={mau === m}
                  onChange={() => setMau(m)}
                  className="peer sr-only"
                  aria-label={`Màu ${m.split("-")[1]}`}
                />
                <span
                  aria-hidden
                  className={`block size-7 rounded-nb border-2 border-ink peer-checked:outline peer-checked:outline-[3px] peer-checked:outline-offset-2 peer-checked:outline-ink peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-accent-2 ${lopNhan(m)}`}
                />
              </label>
            ))}
          </div>
        </fieldset>
        <div>
          <NutChinh type="submit" disabled={!ten.trim() || tao.isPending}>
            <Plus aria-hidden className="size-4" /> Tạo nhãn
          </NutChinh>
        </div>
      </form>

      <ul className="mt-4 flex flex-col divide-y-2 divide-line">
        {tatCa.map((t) => (
          <li key={t.id} className="flex items-center gap-3 py-2">
            <span
              className={`rounded-nb border-2 border-ink px-2 py-0.5 text-xs font-bold text-ink ${lopNhan(t.color)} ${t.is_active ? "" : "opacity-60"}`}
            >
              {t.name}
            </span>
            {!t.is_active && <HuyHieu>Ngừng dùng</HuyHieu>}
            <Nut
              bienThe="trong"
              co="sm"
              className="ml-auto"
              disabled={doiTrangThai.isPending}
              onClick={() => doiTrangThai.mutate(t)}
            >
              {t.is_active ? "Ngừng dùng" : "Dùng lại"}
            </Nut>
          </li>
        ))}
      </ul>
    </HopThoai>
  );
}

// ---- Ghi chú --------------------------------------------------------------

export function MucGhiChu({ customerId }: { customerId: string }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const bayGio = useBayGio();
  const [noiDung, setNoiDung] = useState("");
  const [xoa, setXoa] = useState<CustomerNote | null>(null);
  const [loi, setLoi] = useState<string | null>(null);

  const { data: ghiChu = [], isError } = useQuery({
    queryKey: khoaInbox.ghiChu(customerId),
    queryFn: ({ signal }) => layGhiChu(customerId, signal),
  });
  const { data: phong } = useQuery({
    queryKey: khoaPhongBan,
    queryFn: ({ signal }) => layPhongBanHoatDong(signal),
  });
  const tenPhongToi = user?.department_id
    ? (phong?.items.find((p) => p.id === user.department_id)?.name ?? null)
    : null;

  const viet = useMutation({
    mutationFn: () => vietGhiChu(customerId, noiDung),
    onSuccess: (moi) => {
      setNoiDung("");
      setLoi(null);
      qc.setQueryData<CustomerNote[]>(khoaInbox.ghiChu(customerId), (cu) => [moi, ...(cu ?? [])]);
    },
    onError: (e) => setLoi(loiCua(e)),
  });
  const huy = useMutation({
    mutationFn: (id: string) => xoaGhiChu(id),
    onSuccess: (_, id) => {
      setXoa(null);
      qc.setQueryData<CustomerNote[]>(khoaInbox.ghiChu(customerId), (cu) =>
        (cu ?? []).filter((g) => g.id !== id),
      );
    },
    onError: (e) => setLoi(loiCua(e)),
  });

  return (
    <section aria-labelledby="muc-ghi-chu">
      <TieuDeMuc>
        <span id="muc-ghi-chu">Ghi chú nội bộ</span>
      </TieuDeMuc>
      <p className="mb-2 text-xs text-ink-2">
        {nhanPhamViGhiChu(user?.role === "ADMIN" ? null : tenPhongToi)}
      </p>
      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (noiDung.trim()) viet.mutate();
        }}
      >
        <VungNhap
          aria-label="Ghi chú mới"
          value={noiDung}
          maxLength={2000}
          onChange={(e) => setNoiDung(e.target.value)}
          placeholder="Ghi lại điều đồng nghiệp cần biết…"
          className="min-h-16 text-sm"
        />
        <div>
          <Nut type="submit" bienThe="phu" co="sm" disabled={!noiDung.trim()} dangChay={viet.isPending}>
            Lưu ghi chú
          </Nut>
        </div>
      </form>
      {loi && (
        <p role="alert" className="mt-1 text-xs font-semibold text-bad">
          {loi}
        </p>
      )}
      {isError && <p className="mt-2 text-xs text-bad">Không tải được ghi chú.</p>}

      <ul className="mt-3 flex flex-col gap-2">
        {ghiChu.map((g) => (
          <li key={g.id} className="rounded-nb border-2 border-line bg-card px-3 py-2">
            <p className="whitespace-pre-wrap break-words text-sm text-ink">{g.body}</p>
            <div className="mt-1 flex items-center gap-1 text-xs text-ink-2">
              <span className="font-semibold">{g.author_name ?? "—"}</span>
              <span aria-hidden>·</span>
              <time dateTime={g.created_at}>{mocTuongDoi(g.created_at, bayGio)}</time>
              {user?.role === "ADMIN" && (
                <span className="truncate">· {g.department_name ?? "Quản trị viên"}</span>
              )}
              {(g.author_id === user?.id || user?.role === "ADMIN") && (
                <NutIcon
                  icon={Trash2}
                  nhan="Xoá ghi chú"
                  co="sm"
                  className="ml-auto"
                  onClick={() => setXoa(g)}
                />
              )}
            </div>
          </li>
        ))}
      </ul>

      {xoa && (
        <HopXacNhan
          tieuDe="Xoá ghi chú?"
          moTa="Ghi chú sẽ mất hẳn với mọi người trong phòng."
          nhanXacNhan="Xoá ghi chú"
          nguyHiem
          dangChay={huy.isPending}
          loi={loi}
          onDong={() => setXoa(null)}
          onXacNhan={() => huy.mutate(xoa.id)}
        />
      )}
    </section>
  );
}

// ---- Lịch sử --------------------------------------------------------------

export function MucLichSu({ customerId, hienTaiId }: { customerId: string; hienTaiId: string }) {
  const bayGio = useBayGio();
  const { data, isPending, isError } = useQuery({
    queryKey: khoaInbox.lichSu(customerId),
    queryFn: ({ signal }) => layLichSuKhach(customerId, signal),
  });
  const khac = (data?.items ?? []).filter((i) => i.conversation_id !== hienTaiId);

  return (
    <section aria-labelledby="muc-lich-su">
      <TieuDeMuc>
        <span id="muc-lich-su">Hội thoại trước</span>
      </TieuDeMuc>
      {isPending && <p className="text-sm text-ink-2">Đang tải…</p>}
      {isError && <p className="text-sm text-bad">Không tải được lịch sử.</p>}
      {data && khac.length === 0 && (
        <p className="text-sm text-ink-2">Chưa có hội thoại nào khác với khách này (trên kênh này).</p>
      )}
      <ul className="flex flex-col gap-1.5">
        {khac.map((i) => (
          <li key={i.conversation_id}>
            <Link
              href={`/inbox/${i.conversation_id}`}
              className="block rounded-nb border-2 border-line px-3 py-2 hover:border-ink hover:bg-sunken"
            >
              <span className="flex items-center justify-between gap-2 text-xs">
                <HuyHieu tong={i.status === "DA_DONG" ? "trung" : i.status === "CHO_PHAN" ? "wait" : "info"}>
                  {NHAN_TRANG_THAI[i.status]}
                </HuyHieu>
                <time dateTime={i.last_message_at} className="text-ink-2">
                  {mocTuongDoi(i.last_message_at, bayGio)}
                </time>
              </span>
              <span className="mt-1 block truncate text-sm text-ink">
                {i.last_message_preview ?? "—"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
