"use client";

/**
 * Khung chat của một hội thoại (spec §4.2 cột phải).
 *
 * Luồng trả lời theo §4.4: khoá ô → `POST reply` → dùng tin từ response cập
 * nhật cache → mở khoá. Lỗi thì GIỮ nội dung đã gõ (IT-5) và refetch để đồng
 * bộ trạng thái thật khi server báo xung đột (409/422).
 */

import { useEffect, useRef, useState } from "react";
import { t } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api-client";
import {
  dongHoiThoai,
  khoaInbox,
  layChiTietHoiThoai,
  nhanViec,
  SO_TIN_MOI_LAN,
  phanPhong,
  traLoiHoiThoai,
} from "@/lib/inbox-api";
import { chuCaiDau, tenKhach } from "@/lib/hien-thi";
import { useAuth } from "@/lib/auth-context";
import {
  hienDong,
  hienNhanViec,
  hienPhanPhong,
  type Actor,
} from "@/lib/quyen-hanh-dong";
import type { Conversation, Message } from "@/lib/types";
import { BadgeKenh, BadgeTrangThai } from "./badges";
import { BongBongTin } from "./bong-bong-tin";
import { DialogPhanPhong } from "./dialog-phan-phong";
import { OSoanTin } from "./o-soan-tin";

export function KhungChat({ conversationId }: { conversationId: string }) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [loiGui, setLoiGui] = useState<string | null>(null);
  const [loiHanhDong, setLoiHanhDong] = useState<string | null>(null);
  const [moDialogPhan, setMoDialogPhan] = useState(false);
  const [hetTinCu, setHetTinCu] = useState(false);

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: khoaInbox.detail(conversationId),
    queryFn: ({ signal }) => layChiTietHoiThoai(conversationId, undefined, 0, signal),
  });

  /**
   * Cập nhật sau một hành động.
   *
   * Take/Close/Assign trả `Conversation` KHÔNG kèm `messages`, nên phải giữ lại
   * mảng tin đang có — ghi đè thẳng response sẽ làm trắng khung chat.
   */
  function apDungHoiThoaiMoi(moi: Conversation) {
    setLoiHanhDong(null);
    queryClient.setQueryData<Conversation>(
      khoaInbox.detail(conversationId),
      (cu) => ({ ...moi, messages: moi.messages ?? cu?.messages ?? [] }),
    );
    void queryClient.invalidateQueries({ queryKey: khoaInbox.all });
  }

  /** Lỗi chung của ba hành động: báo rõ rồi đọc lại để đồng bộ trạng thái thật. */
  function xuLyLoiHanhDong(err: unknown) {
    if (err instanceof ApiError) {
      setLoiHanhDong(err.message);
      // 409/422 = trạng thái FE đang giữ đã cũ; 403/404 = mất quyền hoặc đã đổi
      // phòng. Cả hai đều cần đọc lại để nút hiển thị cho đúng.
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
    onSuccess: apDungHoiThoaiMoi,
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

  /**
   * Tải thêm tin CŨ HƠN khi người dùng cuộn lên đầu.
   *
   * Backend trả `limit` tin mới nhất; `offset` đếm ngược từ mới về cũ, nên
   * offset = số tin đang có sẽ lấy đúng trang liền trước.
   */
  const taiThem = useMutation({
    mutationFn: () => {
      const dangCo = queryClient.getQueryData<Conversation>(
        khoaInbox.detail(conversationId),
      );
      return layChiTietHoiThoai(
        conversationId,
        SO_TIN_MOI_LAN,
        dangCo?.messages.length ?? 0,
      );
    },
    onSuccess: (trang) => {
      if (trang.messages.length === 0) {
        setHetTinCu(true);
        return;
      }
      if (trang.messages.length < SO_TIN_MOI_LAN) setHetTinCu(true);
      queryClient.setQueryData<Conversation>(
        khoaInbox.detail(conversationId),
        (cu) => {
          if (!cu) return cu;
          // Lọc trùng: tin mới có thể tới giữa hai lần tải và làm lệch offset.
          const daCo = new Set(cu.messages.map((m) => m.id));
          const themVao = trang.messages.filter((m) => !daCo.has(m.id));
          return { ...cu, messages: [...themVao, ...cu.messages] };
        },
      );
    },
  });

  // Đủ một trang đầy nghĩa là có thể còn tin cũ hơn.
  const conCuHon = !hetTinCu && (data?.messages.length ?? 0) >= SO_TIN_MOI_LAN;

  const guiTraLoi = useMutation({
    mutationFn: ({ text, tep }: { text: string; tep: File[] }) =>
      traLoiHoiThoai(conversationId, text, tep),
    onSuccess: (tinMoi: Message) => {
      setLoiGui(null);
      // Dùng thẳng tin từ response thay vì gọi lại API (RB-6): response đã là
      // trạng thái mới nhất của server.
      queryClient.setQueryData<Conversation>(
        khoaInbox.detail(conversationId),
        (cu) =>
          cu ? { ...cu, messages: [...cu.messages, tinMoi] } : cu,
      );
      // Dòng bên trái phải nhảy lên đầu và đổi mốc thời gian.
      void queryClient.invalidateQueries({ queryKey: khoaInbox.all });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setLoiGui(err.message);
        // 409/422 nghĩa là trạng thái FE đang giữ đã cũ (ai đó vừa đóng hội
        // thoại chẳng hạn) — đọc lại để ô soạn khoá/mở cho đúng.
        if (err.isConflict || err.isForbidden) void refetch();
      } else {
        setLoiGui(t("soan.loiGuiChung"));
      }
    },
  });

  if (isPending) {
    return (
      <div className="flex flex-1 items-center justify-center bg-surface">
        <p className="text-sm text-muted">{t("chat.dangTaiHoiThoai")}</p>
      </div>
    );
  }

  if (isError) {
    const la404 = error instanceof ApiError && error.isForbidden;
    return (
      <div className="flex flex-1 items-center justify-center bg-surface px-6">
        <div className="max-w-sm text-center">
          <p className="text-sm font-medium text-foreground">
            {la404 ? t("chat.khongCoQuyen") : t("chat.loiTai")}
          </p>
          <p className="mt-1 text-xs text-muted">
            {error instanceof ApiError
              ? error.message
              : t("chung.loiKetNoi")}
          </p>
          {!la404 && (
            <button
              type="button"
              onClick={() => void refetch()}
              className="mt-4 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95"
            >
              {t("chung.thuLai")}
            </button>
          )}
        </div>
      </div>
    );
  }

  const actor: Actor | null = user
    ? { role: user.role, department_id: user.department_id }
    : null;

  return (
    <section className="flex min-w-0 flex-1 flex-col bg-surface">
      <HeaderHoiThoai
        hoiThoai={data}
        actor={actor}
        dangNhanViec={dangNhanViec.isPending}
        dangDong={dangDong.isPending}
        onNhanViec={() => dangNhanViec.mutate()}
        onDong={() => dangDong.mutate()}
        onMoPhanPhong={() => {
          setLoiHanhDong(null);
          setMoDialogPhan(true);
        }}
      />

      {loiHanhDong && (
        <p
          role="alert"
          className="mx-4 mt-2 rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2 text-xs text-danger-fg"
        >
          {loiHanhDong}
        </p>
      )}

      <DanhSachTin
        messages={data.messages}
        conCuHon={conCuHon}
        dangTaiThem={taiThem.isPending}
        onTaiThem={() => taiThem.mutate()}
      />

      {loiGui && (
        <p
          role="alert"
          className="mx-4 mb-2 rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2 text-xs text-danger-fg"
        >
          {loiGui}
        </p>
      )}

      <OSoanTin
        status={data.status}
        dangGui={guiTraLoi.isPending}
        onGui={async (text, tep) => {
          // `mutateAsync` ném lại lỗi → OSoanTin giữ nguyên chữ và ảnh (IT-5).
          await guiTraLoi.mutateAsync({ text, tep });
        }}
      />

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
    </section>
  );
}

function HeaderHoiThoai({
  hoiThoai,
  actor,
  dangNhanViec,
  dangDong,
  onNhanViec,
  onDong,
  onMoPhanPhong,
}: {
  hoiThoai: Conversation;
  actor: Actor | null;
  dangNhanViec: boolean;
  dangDong: boolean;
  onNhanViec: () => void;
  onDong: () => void;
  onMoPhanPhong: () => void;
}) {
  const ten = tenKhach(hoiThoai.customer_display_name);

  // Ẩn/hiện chỉ để UX gọn; server vẫn là trọng tài cuối (RB-3).
  const coNhanViec = actor ? hienNhanViec(actor, hoiThoai) : false;
  const coDong = actor ? hienDong(actor, hoiThoai) : false;
  const coPhanPhong = actor ? hienPhanPhong(actor, hoiThoai) : false;

  return (
    <header className="flex items-center gap-3 border-b border-border-subtle bg-white px-4 py-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface text-sm font-semibold text-muted">
        {chuCaiDau(hoiThoai.customer_display_name)}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-foreground">{ten}</h2>
          <BadgeKenh platform={hoiThoai.platform} />
          <BadgeTrangThai status={hoiThoai.status} />
        </div>
        <p className="mt-0.5 text-xs text-muted">
          {hoiThoai.department_id ? t("chat.daPhanPhong") : t("chat.chuaPhanPhong")}
          {" · "}
          {hoiThoai.assigned_user_id ? t("chat.dangXuLy") : t("chat.chuaCoNguoiXuLy")}
        </p>
      </div>

      <div className="flex shrink-0 gap-2">
        {coPhanPhong && (
          <button
            type="button"
            onClick={onMoPhanPhong}
            className="rounded-lg bg-primary px-3.5 py-2 text-sm font-semibold text-white transition hover:brightness-95"
          >
            {t("hanhDong.phanPhong")}
          </button>
        )}

        {coNhanViec && (
          <button
            type="button"
            onClick={onNhanViec}
            disabled={dangNhanViec}
            className="rounded-lg border border-border-subtle px-3.5 py-2 text-sm font-medium text-foreground transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            {dangNhanViec ? t("hanhDong.dangNhan") : t("hanhDong.nhanViec")}
          </button>
        )}

        {coDong && (
          <button
            type="button"
            onClick={onDong}
            disabled={dangDong}
            className="rounded-lg border border-border-subtle px-3.5 py-2 text-sm font-medium text-foreground transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            {dangDong ? t("hanhDong.dangDong") : t("hanhDong.dong")}
          </button>
        )}
      </div>
    </header>
  );
}

function DanhSachTin({
  messages,
  conCuHon,
  dangTaiThem,
  onTaiThem,
}: {
  messages: Message[];
  conCuHon: boolean;
  dangTaiThem: boolean;
  onTaiThem: () => void;
}) {
  const cuoiRef = useRef<HTMLDivElement>(null);
  const khungRef = useRef<HTMLDivElement>(null);
  // Chiều cao nội dung trước khi chèn tin cũ, để bù lại vị trí cuộn.
  const caoTruocRef = useRef<number | null>(null);
  const idCuoiRef = useRef<string | null>(null);

  useEffect(() => {
    const khung = khungRef.current;
    if (!khung) return;

    if (caoTruocRef.current !== null) {
      // Vừa chèn tin CŨ vào đầu: dịch vị trí cuộn xuống đúng phần vừa thêm, để
      // nội dung người dùng đang đọc đứng yên thay vì nhảy vọt lên.
      khung.scrollTop += khung.scrollHeight - caoTruocRef.current;
      caoTruocRef.current = null;
      return;
    }

    // Tin MỚI ở cuối (hoặc lần mở đầu) → trôi xuống đáy.
    const idCuoi = messages[messages.length - 1]?.id ?? null;
    if (idCuoi !== idCuoiRef.current) {
      idCuoiRef.current = idCuoi;
      cuoiRef.current?.scrollIntoView({ block: "end" });
    }
  }, [messages]);

  function taiThem() {
    // Ghi lại chiều cao TRƯỚC khi dữ liệu đổi; effect ở trên dùng nó để bù.
    caoTruocRef.current = khungRef.current?.scrollHeight ?? null;
    onTaiThem();
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <p className="text-xs text-muted">{t("chat.chuaCoTin")}</p>
      </div>
    );
  }

  return (
    <div ref={khungRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
      {conCuHon && (
        <div className="flex justify-center pb-1">
          <button
            type="button"
            onClick={taiThem}
            disabled={dangTaiThem}
            className="rounded-full border border-border-subtle bg-white px-3 py-1 text-xs font-medium text-muted transition hover:bg-surface disabled:opacity-60"
          >
            {dangTaiThem ? t("chung.dangTai") : t("chat.xemTinCu")}
          </button>
        </div>
      )}

      {messages.map((m) => (
        <BongBongTin key={m.id} message={m} />
      ))}
      <div ref={cuoiRef} />
    </div>
  );
}
