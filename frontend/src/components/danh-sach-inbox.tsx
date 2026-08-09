"use client";

/**
 * Cột trái: danh sách hội thoại có lọc trạng thái + phân trang (spec §4.2).
 *
 * Bộ lọc và trang giữ trên URL (`?status=&offset=`) thay vì trong state: người
 * dùng tải lại trang hay chia sẻ link vẫn thấy đúng chỗ đang xem, và nút lùi
 * của trình duyệt hoạt động đúng nghĩa.
 */

import { useEffect, useState } from "react";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams, useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useDebounce } from "@/lib/use-debounce";
import { ApiError } from "@/lib/api-client";
import {
  KICH_THUOC_TRANG,
  khoaInbox,
  layDanhSachInbox,
} from "@/lib/inbox-api";
import { NHAN_TRANG_THAI } from "@/lib/hien-thi";
import type { ConversationStatus } from "@/lib/types";
import { DongHoiThoai } from "./dong-hoi-thoai";

/** Các chip lọc. `undefined` = tất cả. */
const BO_LOC: { nhan: string; giaTri?: ConversationStatus }[] = [
  { nhan: t("inbox.locTatCa") },
  { nhan: NHAN_TRANG_THAI.CHO_PHAN, giaTri: "CHO_PHAN" },
  { nhan: NHAN_TRANG_THAI.DANG_MO, giaTri: "DANG_MO" },
  { nhan: NHAN_TRANG_THAI.DA_DONG, giaTri: "DA_DONG" },
];

function laTrangThaiHopLe(v: string | null): v is ConversationStatus {
  return v === "CHO_PHAN" || v === "DANG_MO" || v === "DA_DONG";
}

export function DanhSachInbox() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams<{ id?: string }>();
  const { user } = useAuth();

  const thamSoStatus = searchParams.get("status");
  const status = laTrangThaiHopLe(thamSoStatus) ? thamSoStatus : undefined;
  const offset = Math.max(0, Number(searchParams.get("offset") ?? 0) || 0);
  const qTrenUrl = searchParams.get("q") ?? "";

  // Ô tìm kiếm gõ tới đâu hiện tới đó, nhưng chỉ gọi API sau khi ngừng gõ —
  // gọi mỗi ký tự vừa tốn vừa làm danh sách nhấp nháy.
  const [oTimKiem, setOTimKiem] = useState(qTrenUrl);
  const q = useDebounce(oTimKiem, 350);

  const thamSo = {
    status,
    limit: KICH_THUOC_TRANG,
    offset,
    q: q.trim() || undefined,
  };

  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: khoaInbox.list(thamSo),
    queryFn: ({ signal }) => layDanhSachInbox(thamSo, signal),
  });

  /**
   * Staff không được server trả về hội thoại `CHO_PHAN` (use case ép phạm vi
   * theo vai). Ẩn chip đó cho khỏi gây hiểu nhầm — nhưng đây chỉ là UX, dữ liệu
   * vẫn do server lọc (RB-3).
   */
  const boLocHienThi = BO_LOC.filter(
    (b) => !(b.giaTri === "CHO_PHAN" && user?.role === "STAFF"),
  );

  function dieuHuong(thayDoi: {
    status?: ConversationStatus;
    offset?: number;
    q?: string;
  }) {
    const sp = new URLSearchParams(searchParams.toString());

    if ("status" in thayDoi) {
      if (thayDoi.status) sp.set("status", thayDoi.status);
      else sp.delete("status");
      // Đổi bộ lọc thì về trang đầu: giữ offset cũ dễ rơi vào trang trống.
      sp.delete("offset");
    }
    if ("q" in thayDoi) {
      if (thayDoi.q) sp.set("q", thayDoi.q);
      else sp.delete("q");
      sp.delete("offset");
    }
    if (thayDoi.offset !== undefined) {
      if (thayDoi.offset > 0) sp.set("offset", String(thayDoi.offset));
      else sp.delete("offset");
    }

    const duoi = sp.toString();
    // Giữ nguyên route hiện tại: component này cũng hiển thị ở `/inbox/[id]`,
    // nên ghi cứng "/inbox" sẽ đá người dùng ra khỏi hội thoại đang mở mỗi lần
    // họ gõ tìm kiếm, đổi chip lọc hay sang trang.
    const goc = params?.id ? `/inbox/${params.id}` : "/inbox";
    const duong = duoi ? `${goc}?${duoi}` : goc;
    // `replace` chứ không `push` cho tìm kiếm: mỗi nhịp gõ tạo một mục lịch sử
    // sẽ khiến nút lùi phải bấm hàng chục lần mới thoát khỏi ô tìm kiếm.
    if ("q" in thayDoi) router.replace(duong);
    else router.push(duong);
  }

  // Đưa từ khoá đã ngừng gõ lên URL để tải lại trang / chia sẻ link vẫn giữ.
  useEffect(() => {
    const hienTai = searchParams.get("q") ?? "";
    const moi = q.trim();
    if (hienTai === moi) return;
    dieuHuong({ q: moi });
    // `dieuHuong` đọc searchParams mới mỗi lần render nên không đưa vào deps —
    // đưa vào sẽ tạo vòng lặp cập nhật.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const tong = data?.total ?? 0;
  const tuSo = tong === 0 ? 0 : offset + 1;
  const denSo = Math.min(offset + KICH_THUOC_TRANG, tong);
  const conTrangTruoc = offset > 0;
  const conTrangSau = offset + KICH_THUOC_TRANG < tong;

  return (
    <aside className="flex w-[360px] shrink-0 flex-col border-r border-border-subtle bg-white">
      <div className="border-b border-border-subtle px-4 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-base font-semibold text-foreground">{t("inbox.tieuDe")}</h1>
          {isFetching && !isPending && (
            <span className="text-[11px] text-muted-soft">{t("inbox.dangCapNhat")}</span>
          )}
        </div>

        <div className="relative mt-2.5">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-soft">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
          </span>
          <input
            type="search"
            value={oTimKiem}
            onChange={(e) => setOTimKiem(e.target.value)}
            placeholder={t("inbox.timKiem")}
            aria-label={t("inbox.timKiemNhan")}
            className="w-full rounded-lg border border-border-subtle py-2 pl-9 pr-8 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
          {oTimKiem && (
            <button
              type="button"
              onClick={() => setOTimKiem("")}
              aria-label={t("inbox.xoaTimKiem")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-soft transition hover:text-muted"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {boLocHienThi.map((b) => {
            const dangChon = status === b.giaTri;
            return (
              <button
                key={b.nhan}
                type="button"
                onClick={() => dieuHuong({ status: b.giaTri })}
                aria-pressed={dangChon}
                className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                  dangChon
                    ? "bg-primary text-white"
                    : "bg-surface text-muted hover:bg-border-subtle"
                }`}
              >
                {b.nhan}
              </button>
            );
          })}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isPending && <KhungCho />}

        {isError && (
          <TrangThaiTrong
            tieuDe={t("inbox.loiTai")}
            moTa={
              error instanceof ApiError
                ? error.message
                : t("chung.loiKetNoi")
            }
            hanhDong={
              <button
                type="button"
                onClick={() => void refetch()}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95"
              >
                {t("chung.thuLai")}
              </button>
            }
          />
        )}

        {!isPending && !isError && data.items.length === 0 && (
          <TrangThaiTrong
            tieuDe={q.trim() ? t("inbox.khongTimThay") : t("inbox.khongCoHoiThoai")}
            moTa={
              q.trim()
                ? `Không có khách nào tên khớp "${q.trim()}".`
                : status
                  ? `Không có hội thoại ở trạng thái "${NHAN_TRANG_THAI[status]}".`
                  : t("inbox.goiYKhiRong")
            }
            hanhDong={
              q.trim() ? (
                <button
                  type="button"
                  onClick={() => setOTimKiem("")}
                  className="rounded-lg border border-border-subtle px-3 py-1.5 text-xs font-medium text-muted transition hover:bg-surface"
                >
                  {t("inbox.xoaTimKiem")}
                </button>
              ) : undefined
            }
          />
        )}

        {!isPending &&
          !isError &&
          data.items.map((item) => (
            <DongHoiThoai
              key={item.conversation_id}
              item={item}
              dangChon={params?.id === item.conversation_id}
            />
          ))}
      </div>

      <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2.5">
        <span className="text-[11px] text-muted">
          {tong === 0 ? "0 hội thoại" : `${tuSo}–${denSo} / ${tong}`}
        </span>
        <div className="flex gap-1">
          <NutTrang
            nhan="‹"
            moTa={t("inbox.trangTruoc")}
            tat={!conTrangTruoc}
            onClick={() =>
              dieuHuong({ offset: Math.max(0, offset - KICH_THUOC_TRANG) })
            }
          />
          <NutTrang
            nhan="›"
            moTa={t("inbox.trangSau")}
            tat={!conTrangSau}
            onClick={() => dieuHuong({ offset: offset + KICH_THUOC_TRANG })}
          />
        </div>
      </div>
    </aside>
  );
}

function NutTrang({
  nhan,
  moTa,
  tat,
  onClick,
}: {
  nhan: string;
  moTa: string;
  tat: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={tat}
      aria-label={moTa}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-border-subtle text-sm text-muted transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-40"
    >
      {nhan}
    </button>
  );
}

/** Khung xám nhấp nháy trong lúc chờ — đỡ giật hơn là hiện chữ "Đang tải". */
function KhungCho() {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex animate-pulse gap-3">
          <div className="h-9 w-9 shrink-0 rounded-full bg-surface" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-2/3 rounded bg-surface" />
            <div className="h-3 w-1/3 rounded bg-surface" />
          </div>
        </div>
      ))}
    </div>
  );
}

function TrangThaiTrong({
  tieuDe,
  moTa,
  hanhDong,
}: {
  tieuDe: string;
  moTa: string;
  hanhDong?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <p className="text-sm font-medium text-foreground">{tieuDe}</p>
      <p className="text-xs text-muted">{moTa}</p>
      {hanhDong}
    </div>
  );
}
