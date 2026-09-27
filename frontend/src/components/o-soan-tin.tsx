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
import { Info, MessageSquareText, Paperclip, SendHorizontal, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { lenhMau, locMau } from "@/lib/hop-thu";
import type { ConversationStatus, ReplyTemplate } from "@/lib/types";
import { DanhSachMau, HopQuanLyMau, ID_DANH_SACH_MAU, idMucMau, useMau } from "./mau-tra-loi";
import { Nut } from "./ui/nut";
import { NutIcon } from "./ui/nut-icon";

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

  // ---- Mẫu trả lời (BE-7): gõ "/" ở đầu ô hoặc bấm nút ----
  const { user } = useAuth();
  const { data: tatCaMau = [], isPending: dangTaiMau } = useMau();
  const [moTay, setMoTay] = useState(false);
  const [dongTay, setDongTay] = useState(false);
  const [chiSo, setChiSo] = useState(0);
  const [moQuanLyMau, setMoQuanLyMau] = useState(false);
  const chuLenh = lenhMau(noiDung);
  const moMau = !dongTay && (chuLenh !== null || moTay);
  const mauKhop = locMau(tatCaMau, chuLenh ?? "");
  const chiSoHopLe = Math.min(chiSo, Math.max(mauKhop.length - 1, 0));

  function chonMau(m: ReplyTemplate) {
    const o = oRef.current;
    if (chuLenh !== null || !o) {
      setNoiDung(m.body); // "/bao gia" → thay cả lệnh bằng nội dung mẫu
    } else {
      // Mở bằng nút: chèn tại con trỏ, giữ phần đã gõ.
      const dau = o.selectionStart ?? noiDung.length;
      const cuoi = o.selectionEnd ?? dau;
      setNoiDung(noiDung.slice(0, dau) + m.body + noiDung.slice(cuoi));
    }
    setMoTay(false);
    o?.focus();
  }
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
    if (moMau) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const n = mauKhop.length;
        if (n) setChiSo((chiSoHopLe + (e.key === "ArrowDown" ? 1 : n - 1)) % n);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setMoTay(false);
        setDongTay(true);
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        // Danh sách đang mở: Enter chèn mẫu, KHÔNG gửi "/bao gia" cho khách.
        e.preventDefault();
        if (mauKhop[chiSoHopLe]) chonMau(mauKhop[chiSoHopLe]);
        return;
      }
    }
    // Enter gửi, Shift+Enter xuống dòng — thói quen của mọi ứng dụng chat.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void gui();
    }
  }

  if (khoa) {
    return (
      <div className="border-t-2 border-ink bg-card px-4 py-3">
        <p className="flex items-center gap-2 rounded-nb border-2 border-dashed border-ink-2 bg-sunken px-3.5 py-3 text-sm font-semibold text-ink-2">
          <Info aria-hidden className="size-4 shrink-0" strokeWidth={2.5} />
          {khoa}
        </p>
      </div>
    );
  }

  return (
    <div className="relative border-t-2 border-ink bg-card px-4 pb-2 pt-3">
      {moMau && (
        <DanhSachMau
          mau={mauKhop}
          chiSo={chiSoHopLe}
          dangTai={dangTaiMau}
          onChon={chonMau}
          onQuanLy={
            user?.role === "MANAGER" || user?.role === "ADMIN"
              ? () => {
                  setMoTay(false);
                  setMoQuanLyMau(true);
                }
              : undefined
          }
        />
      )}
      {moQuanLyMau && <HopQuanLyMau onDong={() => setMoQuanLyMau(false)} />}
      {anh.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {anh.map((a) => (
            <div key={a.xemTruoc} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={a.xemTruoc}
                alt={a.file.name}
                className="size-16 rounded-nb border-2 border-ink object-cover"
              />
              <button
                type="button"
                onClick={() => boAnh(a.xemTruoc)}
                aria-label={`Bỏ ảnh ${a.file.name}`}
                className="absolute -right-2 -top-2 flex size-6 items-center justify-center rounded-full border-2 border-ink bg-card text-ink hover:bg-bad hover:text-white"
              >
                <X aria-hidden className="size-3.5" strokeWidth={3} />
              </button>
            </div>
          ))}
        </div>
      )}

      {loiTep && (
        <p role="alert" className="mb-2 text-xs font-semibold text-bad">
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
        <NutIcon
          icon={Paperclip}
          nhan={t("soan.dinhKemAnh")}
          onClick={() => oTepRef.current?.click()}
          disabled={dangGui}
        />

        <NutIcon
          icon={MessageSquareText}
          nhan="Mẫu trả lời (gõ / ở đầu ô)"
          aria-expanded={moMau}
          onClick={() => {
            setDongTay(false);
            setMoTay((cu) => !cu);
            oRef.current?.focus();
          }}
          disabled={dangGui}
        />

        <textarea
          ref={oRef}
          rows={1}
          value={noiDung}
          maxLength={DAI_TOI_DA}
          disabled={dangGui}
          onChange={(e) => {
            setNoiDung(e.target.value);
            setDongTay(false);
            setChiSo(0);
          }}
          onKeyDown={xuLyPhim}
          aria-controls={moMau ? ID_DANH_SACH_MAU : undefined}
          aria-activedescendant={moMau && mauKhop.length ? idMucMau(chiSoHopLe) : undefined}
          placeholder={t("soan.nhapNoiDung")}
          aria-label={t("soan.nhan")}
          aria-describedby="goi-y-phim-soan"
          className="min-h-10 flex-1 resize-none rounded-nb border-2 border-ink bg-card px-3.5 py-2 text-sm text-ink placeholder:text-ink-2 disabled:bg-sunken"
        />

        <Nut icon={SendHorizontal} onClick={() => void gui()} disabled={trong || dangGui}>
          {dangGui ? t("soan.dangGui") : t("soan.gui")}
        </Nut>
      </div>

      <div className="mt-1.5 flex justify-between text-xs text-ink-2">
        <span id="goi-y-phim-soan">
          <kbd className="font-sans font-bold">Enter</kbd> để gửi · <kbd className="font-sans font-bold">Shift+Enter</kbd> xuống dòng · <kbd className="font-sans font-bold">/</kbd> mẫu trả lời
        </span>
        {noiDung.length > DAI_TOI_DA - 500 && (
          <span>
            {noiDung.length}/{DAI_TOI_DA}
          </span>
        )}
      </div>
    </div>
  );
}
