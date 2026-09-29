"use client";

/**
 * Cột trái Hộp thư (redesign 2a §4.1): tab Của tôi / Chưa ai nhận / Tất cả (BE-3),
 * ô chọn trạng thái, tìm theo tên, cuộn liên tục.
 *
 * Bộ lọc giữ trên URL (`?loc=&status=&q=`): tải lại / chia sẻ link / nút lùi đều
 * đúng. Không có `offset` trên URL nữa — cuộn liên tục thay cho phân trang.
 */

import { useEffect, useRef, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Inbox, SearchX, X, Search } from "lucide-react";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { useDebounce } from "@/lib/use-debounce";
import { useBayGio } from "@/lib/use-bay-gio";
import { ApiError } from "@/lib/api-client";
import {
  KICH_THUOC_TRANG,
  khoaInbox,
  layDanhSachInbox,
  layDemChuaDoc,
  type LocNguoiPhuTrach,
} from "@/lib/inbox-api";
import { gopTrang, tieuDeCoSoChuaDoc } from "@/lib/hop-thu";
import { NHAN_TRANG_THAI } from "@/lib/hien-thi";
import type { ConversationStatus, Role } from "@/lib/types";
import { DongHoiThoai } from "./dong-hoi-thoai";
import { OChon, ONhap } from "./ui/o-nhap";
import { NutIcon } from "./ui/nut-icon";
import { Nut } from "./ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "./ui/trang-thai";

type Loc = "cua-toi" | "chua-nhan" | "tat-ca";

const TAB: { loc: Loc; nhan: string; assignee?: LocNguoiPhuTrach }[] = [
  { loc: "cua-toi", nhan: "Của tôi", assignee: "me" },
  { loc: "chua-nhan", nhan: "Chưa ai nhận", assignee: "none" },
  { loc: "tat-ca", nhan: "Tất cả" },
];

/** Mặc định theo vai: Staff làm việc của mình; Manager/Admin nhìn toàn cảnh. */
const locMacDinh = (vai: Role | undefined): Loc => (vai === "STAFF" ? "cua-toi" : "tat-ca");

function laTrangThai(v: string | null): v is ConversationStatus {
  return v === "CHO_PHAN" || v === "DANG_MO" || v === "DA_DONG";
}
function laLoc(v: string | null): v is Loc {
  return v === "cua-toi" || v === "chua-nhan" || v === "tat-ca";
}

export function DanhSachInbox() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = useParams<{ id?: string }>();
  const { user } = useAuth();
  const bayGio = useBayGio();

  const locUrl = searchParams.get("loc");
  const loc: Loc = laLoc(locUrl) ? locUrl : locMacDinh(user?.role);
  const statusUrl = searchParams.get("status");
  const status = laTrangThai(statusUrl) ? statusUrl : undefined;

  // Gõ tới đâu hiện tới đó, chỉ gọi API khi ngừng gõ.
  const [oTimKiem, setOTimKiem] = useState(searchParams.get("q") ?? "");
  const q = useDebounce(oTimKiem, 350).trim();

  const boLoc = {
    status,
    q: q || undefined,
    assignee: TAB.find((x) => x.loc === loc)?.assignee,
  };

  const { data, isPending, isError, error, refetch, isFetching, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: khoaInbox.list(boLoc),
      queryFn: ({ pageParam, signal }) =>
        layDanhSachInbox({ ...boLoc, limit: KICH_THUOC_TRANG, offset: pageParam }, signal),
      initialPageParam: 0,
      getNextPageParam: (trang) => {
        const tiep = trang.offset + trang.items.length;
        return trang.items.length > 0 && tiep < trang.total ? tiep : undefined;
      },
      // Có người dùng không đăng nhập xong thì chưa biết mặc định theo vai.
      enabled: Boolean(user),
    });

  const items = data ? gopTrang(data.pages.map((p) => p.items)) : [];

  // Tiêu đề tab "(5) Hộp thư · OmniChat" — cùng cache với huy hiệu nav (không gọi
  // thêm API). Chạy lại khi đổi hội thoại: Next đặt lại <title> lúc điều hướng.
  const { data: chuaDoc } = useQuery({
    queryKey: khoaInbox.chuaDoc,
    queryFn: ({ signal }) => layDemChuaDoc(signal),
    enabled: Boolean(user),
  });
  const soChuaDoc = chuaDoc?.conversations ?? 0;
  useEffect(() => {
    document.title = tieuDeCoSoChuaDoc(document.title, soChuaDoc);
  }, [soChuaDoc, params?.id]);
  // Rời Hộp thư: bỏ tiền tố (màn khác không nói về tin chưa đọc).
  useEffect(() => () => void (document.title = tieuDeCoSoChuaDoc(document.title, 0)), []);

  function dieuHuong(thayDoi: { loc?: Loc; status?: ConversationStatus | null; q?: string }) {
    const sp = new URLSearchParams(searchParams.toString());
    const dat = (k: string, v: string | null | undefined) => (v ? sp.set(k, v) : sp.delete(k));
    if ("loc" in thayDoi) dat("loc", thayDoi.loc === locMacDinh(user?.role) ? null : thayDoi.loc);
    if ("status" in thayDoi) dat("status", thayDoi.status);
    if ("q" in thayDoi) dat("q", thayDoi.q);
    sp.delete("offset"); // link cũ còn offset từ thời phân trang
    const duoi = sp.toString();
    // Giữ route hiện tại: danh sách cũng hiện ở `/inbox/[id]`.
    const goc = params?.id ? `/inbox/${params.id}` : "/inbox";
    const duong = duoi ? `${goc}?${duoi}` : goc;
    // `replace` cho tìm kiếm: mỗi nhịp gõ một mục lịch sử thì nút lùi vô dụng.
    if ("q" in thayDoi) router.replace(duong);
    else router.push(duong);
  }

  useEffect(() => {
    if ((searchParams.get("q") ?? "") === q) return;
    dieuHuong({ q });
    // `dieuHuong` đọc searchParams mới mỗi render — đưa vào deps sẽ lặp vô hạn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  // Cuộn liên tục: mốc ở cuối danh sách lọt vào khung nhìn thì tải trang tiếp.
  const khungRef = useRef<HTMLDivElement>(null);
  const mocRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const moc = mocRef.current;
    if (!moc || !hasNextPage) return;
    const quanSat = new IntersectionObserver(
      (e) => {
        if (e[0]?.isIntersecting && !isFetchingNextPage) void fetchNextPage();
      },
      { root: khungRef.current, rootMargin: "200px" },
    );
    quanSat.observe(moc);
    return () => quanSat.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const tong = data?.pages[0]?.total;

  return (
    <aside className="flex w-[360px] shrink-0 flex-col border-r-2 border-ink bg-card">
      <div className="flex flex-col gap-3 border-b-2 border-ink px-4 pb-3 pt-4">
        <div className="flex items-baseline justify-between">
          <h1 className="text-xl font-extrabold text-ink">{t("inbox.tieuDe")}</h1>
          <span aria-live="polite" className="text-xs text-ink-2">
            {isFetching && !isPending ? t("inbox.dangCapNhat") : tong !== undefined ? `${tong} hội thoại` : ""}
          </span>
        </div>

        <div role="group" aria-label="Lọc theo người phụ trách" className="flex rounded-nb border-2 border-ink">
          {TAB.map((tab) => {
            const chon = tab.loc === loc;
            return (
              <button
                key={tab.loc}
                type="button"
                aria-pressed={chon}
                onClick={() => dieuHuong({ loc: tab.loc })}
                className={`h-9 flex-1 border-l-2 border-ink text-sm font-bold first:border-l-0 ${
                  chon ? "bg-ink text-accent" : "bg-card text-ink hover:bg-sunken"
                }`}
              >
                {tab.nhan}
              </button>
            );
          })}
        </div>

        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-2" />
            <ONhap
              type="search"
              value={oTimKiem}
              onChange={(e) => setOTimKiem(e.target.value)}
              placeholder={t("inbox.timKiem")}
              aria-label={t("inbox.timKiemNhan")}
              className="pl-9 pr-9"
            />
            {oTimKiem && (
              <span className="absolute right-1 top-1/2 -translate-y-1/2">
                <NutIcon icon={X} nhan={t("inbox.xoaTimKiem")} co="sm" onClick={() => setOTimKiem("")} />
              </span>
            )}
          </div>
          <OChon
            aria-label="Lọc theo trạng thái"
            value={status ?? ""}
            onChange={(e) => dieuHuong({ status: laTrangThai(e.target.value) ? e.target.value : null })}
            className="w-[152px] shrink-0"
          >
            <option value="">Mọi trạng thái</option>
            {/* Staff không bao giờ nhận hội thoại chờ phân (server lọc) — ẩn cho khỏi hiểu nhầm. */}
            {user?.role !== "STAFF" && <option value="CHO_PHAN">{NHAN_TRANG_THAI.CHO_PHAN}</option>}
            <option value="DANG_MO">{NHAN_TRANG_THAI.DANG_MO}</option>
            <option value="DA_DONG">{NHAN_TRANG_THAI.DA_DONG}</option>
          </OChon>
        </div>
      </div>

      <div ref={khungRef} className="min-h-0 flex-1 overflow-y-auto">
        {(isPending || !user) && <TrangThaiTai dong={7} />}

        {isError && (
          <TrangThaiLoi
            thongDiep={error instanceof ApiError ? error.message : t("chung.loiKetNoi")}
            onThuLai={() => void refetch()}
          />
        )}

        {data && items.length === 0 && (
          <TrangThaiRong
            icon={q ? SearchX : Inbox}
            tieuDe={q ? t("inbox.khongTimThay") : t("inbox.khongCoHoiThoai")}
            moTa={
              q
                ? `Không có khách nào tên khớp "${q}".`
                : loc === "cua-toi"
                  ? "Bạn chưa phụ trách hội thoại nào. Xem tab Chưa ai nhận để nhận việc."
                  : t("inbox.goiYKhiRong")
            }
            hanhDong={
              q ? (
                <Nut bienThe="phu" co="sm" onClick={() => setOTimKiem("")}>
                  {t("inbox.xoaTimKiem")}
                </Nut>
              ) : undefined
            }
          />
        )}

        {items.map((item) => (
          <DongHoiThoai
            key={item.conversation_id}
            item={item}
            dangChon={params?.id === item.conversation_id}
            bayGio={bayGio}
            boLoc={searchParams.toString()}
          />
        ))}

        <div ref={mocRef} aria-hidden className="h-px" />
        {isFetchingNextPage && <TrangThaiTai dong={2} />}
      </div>
    </aside>
  );
}
