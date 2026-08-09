"use client";

/**
 * Ô soạn tin trả lời (spec §4.2 footer, RB-5).
 *
 * Hai bất biến phải giữ:
 * - **RB-5/IT-2:** chỉ gõ được khi hội thoại `DANG_MO`; ngược lại khoá ô và nói
 *   rõ vì sao, thay vì để người dùng gõ xong mới báo lỗi.
 * - **IT-5:** gửi lỗi thì GIỮ NGUYÊN nội dung đã gõ. Xoá nội dung chỉ sau khi
 *   server xác nhận — mất một đoạn vừa soạn là hỏng việc thật sự.
 */

import { useEffect, useRef, useState } from "react";
import { t } from "@/lib/i18n";
import type { ConversationStatus } from "@/lib/types";

/** Giới hạn của `ReplyRequest` phía backend. */
export const DAI_TOI_DA = 8000;

/**
 * Vì sao ô bị khoá — `null` nghĩa là gõ được.
 *
 * Chỉ xét TRẠNG THÁI, không xét người đang xử lý: use case `ReplyToConversation`
 * của backend chỉ đòi đúng phòng + `DANG_MO`, không đòi người gọi phải là
 * `assigned_user_id`. Khoá thêm theo người xử lý sẽ chặn nhầm Manager và đồng
 * nghiệp cùng phòng vốn được phép trả lời.
 */
export function lyDoKhoa(status: ConversationStatus): string | null {
  if (status === "DANG_MO") return null;
  if (status === "CHO_PHAN") {
    return t("soan.khoaChoPhan");
  }
  return t("soan.khoaDaDong");
}

/** Trần kích thước một ảnh, khớp `ATTACHMENT_MAX_BYTES` của backend. */
const ANH_TOI_DA_BYTE = 10 * 1024 * 1024;

interface AnhDaChon {
  file: File;
  /** URL tạm để xem trước; phải thu hồi khi bỏ chọn để không rò bộ nhớ. */
  xemTruoc: string;
}

export function OSoanTin({
  status,
  dangGui,
  onGui,
}: {
  status: ConversationStatus;
  dangGui: boolean;
  onGui: (text: string, tep: File[]) => Promise<void>;
}) {
  const [noiDung, setNoiDung] = useState("");
  const [anh, setAnh] = useState<AnhDaChon[]>([]);
  const [loiTep, setLoiTep] = useState<string | null>(null);
  const oRef = useRef<HTMLTextAreaElement>(null);
  const oTepRef = useRef<HTMLInputElement>(null);
  const khoa = lyDoKhoa(status);
  // Có ảnh thì gửi được dù không gõ chữ.
  const trong = noiDung.trim().length === 0 && anh.length === 0;

  // Chiều cao ô co giãn theo nội dung, chặn trần để không nuốt hết khung chat.
  useEffect(() => {
    const o = oRef.current;
    if (!o) return;
    o.style.height = "auto";
    o.style.height = `${Math.min(o.scrollHeight, 160)}px`;
  }, [noiDung]);

  // Thu hồi mọi URL xem trước khi component biến mất (đổi hội thoại).
  useEffect(() => {
    return () => {
      for (const a of anh) URL.revokeObjectURL(a.xemTruoc);
    };
    // Chỉ chạy khi unmount: `anh` trong closure là danh sách lúc đó, đủ để dọn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function chonAnh(danhSach: FileList | null) {
    if (!danhSach?.length) return;
    setLoiTep(null);
    const themVao: AnhDaChon[] = [];
    for (const file of Array.from(danhSach)) {
      if (!file.type.startsWith("image/")) {
        setLoiTep(t("soan.chiGuiAnh"));
        continue;
      }
      if (file.size > ANH_TOI_DA_BYTE) {
        setLoiTep(`"${file.name}" vượt quá 10MB.`);
        continue;
      }
      themVao.push({ file, xemTruoc: URL.createObjectURL(file) });
    }
    if (themVao.length) setAnh((cu) => [...cu, ...themVao]);
    // Xoá giá trị input để chọn lại đúng tệp vừa bỏ vẫn kích hoạt onChange.
    if (oTepRef.current) oTepRef.current.value = "";
  }

  function boAnh(xemTruoc: string) {
    setAnh((cu) => cu.filter((a) => a.xemTruoc !== xemTruoc));
    URL.revokeObjectURL(xemTruoc);
  }

  async function gui() {
    if (khoa || trong || dangGui) return;
    const text = noiDung.trim();
    const tep = anh.map((a) => a.file);
    await onGui(text, tep);
    // Chỉ xoá khi onGui KHÔNG ném lỗi — người gọi ném lại nếu server từ chối,
    // nhờ vậy nội dung và ảnh vừa chọn còn nguyên để thử lại (IT-5).
    setNoiDung("");
    for (const a of anh) URL.revokeObjectURL(a.xemTruoc);
    setAnh([]);
    setLoiTep(null);
  }

  function xuLyPhim(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter gửi, Shift+Enter xuống dòng — thói quen của mọi ứng dụng chat.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void gui();
    }
  }

  if (khoa) {
    return (
      <div className="border-t border-border-subtle bg-white px-4 py-3">
        <p className="mb-2 flex items-center gap-1.5 text-xs text-muted">
          <IconThongTin />
          {khoa}
        </p>
        <div className="flex gap-2">
          <div className="flex-1 cursor-not-allowed rounded-lg bg-da-dong-bg px-3.5 py-2.5 text-sm text-muted-soft">
            {t("soan.khongTheNhap")}
          </div>
          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-lg bg-da-dong-bg px-4 text-sm font-semibold text-muted-soft"
          >
            {t("soan.gui")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-border-subtle bg-white px-4 py-3">
      {anh.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {anh.map((a) => (
            <div key={a.xemTruoc} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={a.xemTruoc}
                alt={a.file.name}
                className="h-16 w-16 rounded-md border border-border-subtle object-cover"
              />
              <button
                type="button"
                onClick={() => boAnh(a.xemTruoc)}
                aria-label={`Bỏ ảnh ${a.file.name}`}
                className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-foreground text-white transition hover:brightness-125"
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden>
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {loiTep && (
        <p role="alert" className="mb-2 text-xs text-danger-fg">
          {loiTep}
        </p>
      )}

      <div className="flex items-end gap-2">
        <input
          ref={oTepRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => chonAnh(e.target.files)}
        />
        <button
          type="button"
          onClick={() => oTepRef.current?.click()}
          disabled={dangGui}
          aria-label={t("soan.dinhKemAnh")}
          title={t("soan.dinhKemAnh")}
          className="mb-1.5 text-muted-soft transition hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
        >
          <IconGhim />
        </button>

        <textarea
          ref={oRef}
          rows={1}
          value={noiDung}
          maxLength={DAI_TOI_DA}
          disabled={dangGui}
          onChange={(e) => setNoiDung(e.target.value)}
          onKeyDown={xuLyPhim}
          placeholder={t("soan.nhapNoiDung")}
          aria-label={t("soan.nhan")}
          className="flex-1 resize-none rounded-lg border border-border-subtle px-3.5 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-surface"
        />

        <button
          type="button"
          onClick={() => void gui()}
          disabled={trong || dangGui}
          className="mb-0.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {dangGui ? t("soan.dangGui") : t("soan.gui")}
        </button>
      </div>

      {noiDung.length > DAI_TOI_DA - 500 && (
        <p className="mt-1 text-right text-[11px] text-muted-soft">
          {noiDung.length}/{DAI_TOI_DA}
        </p>
      )}
    </div>
  );
}

function IconThongTin() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  );
}

function IconGhim() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}
