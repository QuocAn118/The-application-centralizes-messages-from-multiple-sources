/**
 * Huy hiệu (badge) — nhãn trạng thái. **KHÔNG bóng, KHÔNG hover** (quy tắc bóng,
 * spec Phần 1 §3.2): nút có bóng nhỏ + phản hồi, huy hiệu thì không — đó là thứ
 * phân biệt nhãn với nút (sửa lỗi "Đang dùng" trông như nút bấm, GĐ1 S6).
 */

export type TongHuyHieu = "trung" | "ok" | "wait" | "bad" | "info";

const TONG: Record<TongHuyHieu, string> = {
  trung: "border-ink-2 bg-sunken text-ink",
  ok: "border-ok bg-ok-bg text-ok",
  wait: "border-wait bg-wait-bg text-wait",
  bad: "border-bad bg-bad-bg text-bad",
  info: "border-accent-2 bg-accent-2-soft text-accent-2",
};

export function HuyHieu({
  tong = "trung",
  lop,
  children,
  className = "",
}: {
  tong?: TongHuyHieu;
  /**
   * Cặp nền + chữ có sẵn thay cho `tong` (vd. `LOP_BADGE_VAI`) — nhóm phân loại
   * (vai, hành động) không phải trạng thái nên không ép vào 5 tông. Viền theo
   * màu chữ.
   */
  lop?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-nb border-2 px-2 py-0.5 text-xs font-bold ${lop ? `border-current ${lop}` : TONG[tong]} ${className}`}
    >
      {children}
    </span>
  );
}
