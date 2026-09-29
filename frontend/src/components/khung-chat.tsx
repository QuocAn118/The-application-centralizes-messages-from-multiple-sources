"use client";

/**
 * Khung chat của một hội thoại (redesign 2a §4.2).
 *
 * Luồng trả lời giữ nguyên: khoá ô → `POST reply` → dùng tin từ response cập
 * nhật cache → mở khoá. Lỗi thì GIỮ nội dung đã gõ (IT-5) và refetch khi server
 * báo xung đột (409/422).
 *
 * Mới ở 2a: ô chọn người phụ trách (BE-2), dòng hệ thống + vạch ngày + gom tin,
 * "Đóng" vào menu "⋯" có xác nhận, đánh dấu đã đọc (BE-1).
 */

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheckBig, Clock, UserRound } from "lucide-react";
import { t } from "@/lib/i18n";
import { ApiError } from "@/lib/api-client";
import {
  danhDauDaDoc,
  dongHoiThoai,
  giaoNguoiPhuTrach,
  khoaInbox,
  khoaPhongBan,
  layChiTietHoiThoai,
  layNguoiCuaPhong,
  layPhongBanHoatDong,
  nhanViec,
  phanPhong,
  SO_TIN_MOI_LAN,
  traLoiHoiThoai,
} from "@/lib/inbox-api";
import { DAU_GACH, NHAN_KENH, tenKhach } from "@/lib/hien-thi";
import { dungDongChat, gioPhut, laChoLau, nhanCho, phutCho } from "@/lib/hop-thu";
import { useAuth } from "@/lib/auth-context";
import { useBayGio } from "@/lib/use-bay-gio";
import {
  hienDoiNguoiPhuTrach,
  hienDong,
  hienNhanViec,
  hienPhanPhong,
  tuyChonNguoiPhuTrach,
  type Actor,
} from "@/lib/quyen-hanh-dong";
import type { Conversation, ConversationEvent, Message } from "@/lib/types";
import { BongBongTin } from "./bong-bong-tin";
import { DialogPhanPhong } from "./dialog-phan-phong";
import { HopXacNhan } from "./hop-xac-nhan";
import { OSoanTin } from "./o-soan-tin";
import { PanelKhach } from "./panel-khach";
import { Avatar } from "./ui/avatar";
import { HuyHieu } from "./ui/huy-hieu";
import { IconKenh } from "./ui/icon-kenh";
import { MenuHanhDong } from "./ui/menu-hanh-dong";
import { Nut } from "./ui/nut";
import { OChon } from "./ui/o-nhap";
import { TrangThaiLoi } from "./ui/trang-thai";

export function KhungChat({ conversationId }: { conversationId: string }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [loiGui, setLoiGui] = useState<string | null>(null);
  const [loiHanhDong, setLoiHanhDong] = useState<string | null>(null);
  const [moDialogPhan, setMoDialogPhan] = useState(false);
  const [moXacNhanDong, setMoXacNhanDong] = useState(false);
  const [hetTinCu, setHetTinCu] = useState(false);

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: khoaInbox.detail(conversationId),
    queryFn: ({ signal }) => layChiTietHoiThoai(conversationId, undefined, 0, signal),
  });

  // Tên phòng: danh sách phòng đang hoạt động (đã cache cho dialog phân phòng).
  const { data: phong } = useQuery({
    queryKey: khoaPhongBan,
    queryFn: ({ signal }) => layPhongBanHoatDong(signal),
  });
  const tenPhong = data?.department_id
    ? (phong?.items.find((p) => p.id === data.department_id)?.name ?? DAU_GACH)
    : null;

  // ---- Đánh dấu đã đọc (BE-1, GĐ1 §10.3) ----------------------------------
  // Chỉ làm mới danh sách + huy hiệu nav, KHÔNG làm mới chi tiết (không đổi gì).
  const danhDau = useMutation({
    mutationFn: () => danhDauDaDoc(conversationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inbox", "list"] });
      void queryClient.invalidateQueries({ queryKey: khoaInbox.chuaDoc });
    },
  });
  const tinVaoCuoi = data?.messages.findLast((m) => m.direction === "INBOUND")?.id;
  const tinVaoDaXetRef = useRef<string | null | undefined>(undefined);
  // Có tin tới lúc tab ở nền mà chưa đánh dấu. KHÔNG dựa `data.unread_count`:
  // `GET /inbox/{id}` không tính số đó (luôn 0) — chỉ danh sách mới tính.
  const boQuaLucONenRef = useRef(false);
  useEffect(() => {
    if (!data) return;
    const lanDau = tinVaoDaXetRef.current === undefined;
    const coTinMoi = tinVaoDaXetRef.current !== (tinVaoCuoi ?? null);
    tinVaoDaXetRef.current = tinVaoCuoi ?? null;
    // Lần đầu = vừa mở hội thoại → luôn đánh dấu. Sau đó chỉ khi có tin mới VÀ
    // cửa sổ đang có focus (tab ở nền mà đánh dấu thì người dùng không biết có tin).
    if (lanDau || (coTinMoi && document.hasFocus())) danhDau.mutate();
    else if (coTinMoi) boQuaLucONenRef.current = true;
    // `danhDau` đổi mỗi render; chỉ phản ứng theo tin vào cuối.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Boolean(data), tinVaoCuoi]);
  // Quay lại tab sau khi có tin lúc vắng mặt → giờ mới thật sự đọc.
  useEffect(() => {
    const khiFocus = () => {
      if (!boQuaLucONenRef.current) return;
      boQuaLucONenRef.current = false;
      danhDau.mutate();
    };
    window.addEventListener("focus", khiFocus);
    return () => window.removeEventListener("focus", khiFocus);
  });

  // ---- Hành động -----------------------------------------------------------
  /** Response hành động đã là hội thoại mới nhất; giữ mảng tin đang có nếu thiếu. */
  function apDungHoiThoaiMoi(moi: Conversation) {
    setLoiHanhDong(null);
    queryClient.setQueryData<Conversation>(khoaInbox.detail(conversationId), (cu) => ({
      ...moi,
      messages: moi.messages ?? cu?.messages ?? [],
    }));
    void queryClient.invalidateQueries({ queryKey: ["inbox", "list"] });
  }

  /** 409/422 = FE giữ trạng thái cũ; 403/404 = mất quyền — đọc lại cho nút đúng. */
  function xuLyLoiHanhDong(err: unknown) {
    if (err instanceof ApiError) {
      setLoiHanhDong(err.message);
      if (err.isConflict || err.isForbidden) void refetch();
    } else {
      setLoiHanhDong(t("hanhDong.loiChung"));
    }
  }

  const dangNhanViec = useMutation({
    mutationFn: () => nhanViec(conversationId),
    onSuccess: apDungHoiThoaiMoi,
    onError: xuLyLoiHanhDong,
  });
  const dangDong = useMutation({
    mutationFn: () => dongHoiThoai(conversationId),
    onSuccess: (moi) => {
      apDungHoiThoaiMoi(moi);
      setMoXacNhanDong(false);
    },
    onError: xuLyLoiHanhDong,
  });
  const dangPhan = useMutation({
    mutationFn: (departmentId: string) => phanPhong(conversationId, departmentId),
    onSuccess: (moi) => {
      apDungHoiThoaiMoi(moi);
      setMoDialogPhan(false);
    },
    onError: xuLyLoiHanhDong,
  });
  const dangDoiNguoi = useMutation({
    mutationFn: (userId: string | null) => giaoNguoiPhuTrach(conversationId, userId),
    onSuccess: apDungHoiThoaiMoi,
    onError: xuLyLoiHanhDong,
  });

  /** Tải tin CŨ HƠN: `offset` đếm từ mới về cũ, nên offset = số tin đang có. */
  const taiThem = useMutation({
    mutationFn: () => {
      const dangCo = queryClient.getQueryData<Conversation>(khoaInbox.detail(conversationId));
      return layChiTietHoiThoai(conversationId, SO_TIN_MOI_LAN, dangCo?.messages.length ?? 0);
    },
    onSuccess: (trang) => {
      if (trang.messages.length < SO_TIN_MOI_LAN) setHetTinCu(true);
      if (trang.messages.length === 0) return;
      queryClient.setQueryData<Conversation>(khoaInbox.detail(conversationId), (cu) => {
        if (!cu) return cu;
        // Lọc trùng: tin mới có thể tới giữa hai lần tải và làm lệch offset.
        const daCo = new Set(cu.messages.map((m) => m.id));
        return { ...cu, messages: [...trang.messages.filter((m) => !daCo.has(m.id)), ...cu.messages] };
      });
    },
  });
  const conCuHon = !hetTinCu && (data?.messages.length ?? 0) >= SO_TIN_MOI_LAN;

  const guiTraLoi = useMutation({
    mutationFn: ({ text, tep }: { text: string; tep: File[] }) =>
      traLoiHoiThoai(conversationId, text, tep),
    onSuccess: (tinMoi: Message) => {
      setLoiGui(null);
      // RB-6: response đã là trạng thái mới nhất — không gọi lại API.
      queryClient.setQueryData<Conversation>(khoaInbox.detail(conversationId), (cu) =>
        cu ? { ...cu, messages: [...cu.messages, tinMoi], waiting_since: null } : cu,
      );
      void queryClient.invalidateQueries({ queryKey: ["inbox", "list"] });
      void queryClient.invalidateQueries({ queryKey: khoaInbox.chuaDoc });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setLoiGui(err.message);
        if (err.isConflict || err.isForbidden) void refetch();
      } else {
        setLoiGui(t("soan.loiGuiChung"));
      }
    },
  });

  if (isPending) {
    return (
      <div className="flex flex-1 items-center justify-center bg-paper">
        <p className="text-sm text-ink-2">{t("chat.dangTaiHoiThoai")}</p>
      </div>
    );
  }

  if (isError) {
    const khongCoQuyen = error instanceof ApiError && error.isForbidden;
    return (
      <div className="flex flex-1 items-center justify-center bg-paper">
        <TrangThaiLoi
          thongDiep={
            khongCoQuyen
              ? t("chat.khongCoQuyen")
              : error instanceof ApiError
                ? error.message
                : t("chung.loiKetNoi")
          }
          onThuLai={khongCoQuyen ? undefined : () => void refetch()}
        />
      </div>
    );
  }

  const actor: Actor | null = user ? { role: user.role, department_id: user.department_id } : null;

  return (
    <div className="flex min-w-0 flex-1">
      <section aria-label="Khung chat" className="flex min-w-0 flex-1 flex-col bg-paper">
        <HeaderHoiThoai
          hoiThoai={data}
          actor={actor}
          tenPhong={tenPhong}
          dangNhanViec={dangNhanViec.isPending}
          dangDoiNguoi={dangDoiNguoi.isPending}
          onNhanViec={() => dangNhanViec.mutate()}
          onDoiNguoi={(id) => dangDoiNguoi.mutate(id)}
          onMoXacNhanDong={() => {
            setLoiHanhDong(null);
            setMoXacNhanDong(true);
          }}
          onMoPhanPhong={() => {
            setLoiHanhDong(null);
            setMoDialogPhan(true);
          }}
        />

        {loiHanhDong && !moDialogPhan && !moXacNhanDong && <ThongBaoLoi>{loiHanhDong}</ThongBaoLoi>}

        <DanhSachTin
          messages={data.messages}
          events={data.events ?? []}
          conCuHon={conCuHon}
          dangTaiThem={taiThem.isPending}
          onTaiThem={() => taiThem.mutate()}
        />

        {loiGui && <ThongBaoLoi>{loiGui}</ThongBaoLoi>}

        <OSoanTin
          status={data.status}
          dangGui={guiTraLoi.isPending}
          onGui={async (text, tep) => {
            // `mutateAsync` ném lại lỗi → OSoanTin giữ nguyên chữ và ảnh (IT-5).
            await guiTraLoi.mutateAsync({ text, tep });
          }}
        />
      </section>

      <PanelKhach hoiThoai={data} tenPhong={tenPhong} />

      {moDialogPhan && actor && (
        <DialogPhanPhong
          actor={actor}
          tenKhach={tenKhach(data.customer_display_name)}
          dangGui={dangPhan.isPending}
          loi={loiHanhDong}
          onDong={() => setMoDialogPhan(false)}
          onXacNhan={(departmentId) => dangPhan.mutate(departmentId)}
        />
      )}

      {moXacNhanDong && (
        <HopXacNhan
          tieuDe="Đóng hội thoại?"
          moTa={`Hội thoại với ${tenKhach(data.customer_display_name)} sẽ chuyển sang Đã đóng và không gửi thêm tin được. Khách nhắn lại sẽ mở hội thoại mới.`}
          nhanXacNhan={t("hanhDong.dong")}
          dangChay={dangDong.isPending}
          loi={loiHanhDong}
          onDong={() => setMoXacNhanDong(false)}
          onXacNhan={() => dangDong.mutate()}
        />
      )}
    </div>
  );
}

function ThongBaoLoi({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="mx-4 mt-2 rounded-nb border-2 border-bad bg-bad-bg px-3.5 py-2 text-sm font-semibold text-bad">
      {children}
    </p>
  );
}

function HeaderHoiThoai({
  hoiThoai,
  actor,
  tenPhong,
  dangNhanViec,
  dangDoiNguoi,
  onNhanViec,
  onDoiNguoi,
  onMoXacNhanDong,
  onMoPhanPhong,
}: {
  hoiThoai: Conversation;
  actor: Actor | null;
  tenPhong: string | null;
  dangNhanViec: boolean;
  dangDoiNguoi: boolean;
  onNhanViec: () => void;
  onDoiNguoi: (userId: string | null) => void;
  onMoXacNhanDong: () => void;
  onMoPhanPhong: () => void;
}) {
  const bayGio = useBayGio();
  const cho = phutCho(hoiThoai.waiting_since, bayGio);

  // Ẩn/hiện chỉ để UX gọn; server vẫn là trọng tài cuối (RB-3).
  const coNhanViec = actor ? hienNhanViec(actor, hoiThoai) : false;
  const coDong = actor ? hienDong(actor, hoiThoai) : false;
  const coPhanPhong = actor ? hienPhanPhong(actor, hoiThoai) : false;

  return (
    <header className="flex items-center gap-3 border-b-2 border-ink bg-card px-5 py-3">
      <Avatar id={hoiThoai.customer_id} ten={hoiThoai.customer_display_name} />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-lg font-extrabold text-ink">
            {tenKhach(hoiThoai.customer_display_name)}
          </h2>
          {cho !== null && (
            <HuyHieu tong={laChoLau(cho) ? "bad" : "trung"}>
              <Clock aria-hidden className="size-3" strokeWidth={2.5} />
              {nhanCho(cho)}
            </HuyHieu>
          )}
          {hoiThoai.status === "DA_DONG" && <HuyHieu>Đã đóng</HuyHieu>}
        </div>
        {/* Dòng 2: kênh · phòng · người phụ trách — dòng 1 dành cho tên + nút, để
            tên khách không bị cắt khi có cả ô chọn lẫn "Nhận việc" (2b). */}
        <div className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-ink-2">
          <IconKenh kenh={hoiThoai.platform} co={14} />
          {NHAN_KENH[hoiThoai.platform]}
          <span aria-hidden>·</span>
          {tenPhong ?? <span className="font-semibold text-wait">Chờ phân phòng</span>}
          <ONguoiPhuTrach
            hoiThoai={hoiThoai}
            choDoi={actor ? hienDoiNguoiPhuTrach(actor, hoiThoai) : false}
            dangDoi={dangDoiNguoi}
            onDoi={onDoiNguoi}
          />
        </div>
      </div>

      {coPhanPhong && <Nut onClick={onMoPhanPhong}>{t("hanhDong.phanPhong")}</Nut>}
      {coNhanViec && (
        <Nut onClick={onNhanViec} dangChay={dangNhanViec}>
          {dangNhanViec ? t("hanhDong.dangNhan") : t("hanhDong.nhanViec")}
        </Nut>
      )}
      <MenuHanhDong
        nhan="Thao tác khác"
        muc={[{ nhan: t("hanhDong.dong"), icon: CircleCheckBig, nguyHiem: true, an: !coDong, onChon: onMoXacNhanDong }]}
      />
    </header>
  );
}

/**
 * Người phụ trách: Manager (phòng mình) / Admin có ô chọn đổi/gỡ; người khác chỉ
 * thấy chữ. Danh sách người lấy từ `/users` — chỉ gọi khi có ô chọn (Staff bị 403).
 */
function ONguoiPhuTrach({
  hoiThoai,
  choDoi,
  dangDoi,
  onDoi,
}: {
  hoiThoai: Conversation;
  choDoi: boolean;
  dangDoi: boolean;
  onDoi: (userId: string | null) => void;
}) {
  const phongId = hoiThoai.department_id;
  const { data } = useQuery({
    queryKey: khoaInbox.nguoiPhong(phongId ?? ""),
    queryFn: ({ signal }) => layNguoiCuaPhong(phongId!, signal),
    enabled: choDoi && phongId !== null,
    staleTime: 60_000,
  });

  const hienTai = hoiThoai.assigned_user_id
    ? { id: hoiThoai.assigned_user_id, ten: hoiThoai.assigned_user_name ?? DAU_GACH }
    : null;

  if (!choDoi) {
    if (hoiThoai.status === "CHO_PHAN") return null;
    return (
      <p className="flex shrink-0 items-center gap-1.5 text-sm text-ink-2">
        <UserRound aria-hidden className="size-4" />
        Phụ trách:
        <span className="font-bold text-ink">{hienTai?.ten ?? "Chưa ai nhận"}</span>
      </p>
    );
  }

  const tuyChon = tuyChonNguoiPhuTrach(
    (data?.items ?? []).map((u) => ({ id: u.id, ten: u.full_name })),
    hienTai,
  );

  return (
    <label className="flex shrink-0 items-center gap-2 text-sm font-semibold text-ink-2">
      Phụ trách
      <OChon
        value={hienTai?.id ?? ""}
        disabled={dangDoi}
        onChange={(e) => {
          const moi = e.target.value || null;
          if (moi !== (hienTai?.id ?? null)) onDoi(moi);
        }}
        className="w-48 [&_select]:h-8"
      >
        <option value="">{hienTai ? "— Gỡ người phụ trách —" : "— Chưa ai nhận —"}</option>
        {tuyChon.map((n) => (
          <option key={n.id} value={n.id}>
            {n.ten}
          </option>
        ))}
      </OChon>
    </label>
  );
}

function DanhSachTin({
  messages,
  events,
  conCuHon,
  dangTaiThem,
  onTaiThem,
}: {
  messages: Message[];
  events: ConversationEvent[];
  conCuHon: boolean;
  dangTaiThem: boolean;
  onTaiThem: () => void;
}) {
  const bayGio = useBayGio();
  const cuoiRef = useRef<HTMLDivElement>(null);
  const khungRef = useRef<HTMLDivElement>(null);
  // Chiều cao nội dung + tin đầu trước khi bấm "Xem tin cũ", để bù lại vị trí cuộn.
  const truocTaiRef = useRef<{ cao: number; dau: string | undefined } | null>(null);
  const idCuoiRef = useRef<string | null>(null);

  useEffect(() => {
    const khung = khungRef.current;
    if (!khung) return;
    const truoc = truocTaiRef.current;
    truocTaiRef.current = null;
    // Chỉ bù khi tin CŨ thật sự chèn vào đầu (tin đầu đổi). Tải về rỗng / lỗi thì
    // bỏ mốc — nếu giữ, tin realtime kế tiếp sẽ bị coi là tin cũ và không trôi xuống.
    if (truoc && messages[0]?.id !== truoc.dau) {
      khung.scrollTop += khung.scrollHeight - truoc.cao;
      return;
    }
    // Tin/dòng MỚI ở cuối (hoặc lần mở đầu) → trôi xuống đáy.
    const idCuoi = `${messages[messages.length - 1]?.id}:${events.length}`;
    if (idCuoi !== idCuoiRef.current) {
      idCuoiRef.current = idCuoi;
      cuoiRef.current?.scrollIntoView({ block: "end" });
    }
  }, [messages, events]);

  if (messages.length === 0 && events.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <p className="text-sm text-ink-2">{t("chat.chuaCoTin")}</p>
      </div>
    );
  }

  // Tin cũ chưa tải hết thì dòng hệ thống cũ hơn tin cũ nhất cũng chưa nên hiện
  // (sẽ lơ lửng trước khoảng trống). Lọc theo mốc tin cũ nhất đang có.
  const mocCuNhat = conCuHon && messages[0] ? Date.parse(messages[0].created_at) : -Infinity;
  const dong = dungDongChat(
    messages,
    events.filter((e) => Date.parse(e.created_at) >= mocCuNhat),
    bayGio,
  );

  return (
    <div ref={khungRef} className="min-h-0 flex-1 overflow-y-auto px-5 pb-4 pt-2">
      {conCuHon && (
        <div className="flex justify-center pt-2">
          <Nut
            bienThe="phu"
            co="sm"
            dangChay={dangTaiThem}
            onClick={() => {
              const khung = khungRef.current;
              truocTaiRef.current = khung ? { cao: khung.scrollHeight, dau: messages[0]?.id } : null;
              onTaiThem();
            }}
          >
            {dangTaiThem ? t("chung.dangTai") : t("chat.xemTinCu")}
          </Nut>
        </div>
      )}

      {dong.map((d) => {
        if (d.loai === "ngay") {
          return (
            <div key={d.khoa} role="separator" className="mt-5 mb-1 flex items-center gap-3 text-xs font-bold text-ink-2">
              <span className="h-0.5 flex-1 bg-line" />
              {d.nhan}
              <span className="h-0.5 flex-1 bg-line" />
            </div>
          );
        }
        if (d.loai === "su-kien") {
          return (
            <p key={d.khoa} className="mt-3 flex items-center justify-center gap-1.5 text-xs text-ink-2">
              <UserRound aria-hidden className="size-3.5" />
              <span className="font-semibold text-ink">{d.noiDung}</span>
              <span aria-hidden>·</span>
              <time dateTime={d.luc}>
                {gioPhut(d.luc)}
              </time>
            </p>
          );
        }
        return <BongBongTin key={d.khoa} message={d.tin} dauNhom={d.dauNhom} cuoiNhom={d.cuoiNhom} />;
      })}
      <div ref={cuoiRef} />
    </div>
  );
}
