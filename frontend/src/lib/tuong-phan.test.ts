/**
 * Khoá tương phản WCAG AA cho token màu Neo-Brutalism (redesign Phần 1).
 *
 * Đọc hex **thẳng từ `globals.css`** chứ không chép giá trị vào đây: đổi một
 * màu trong CSS mà làm tụt dưới ngưỡng thì test đỏ ngay, không phải nhớ sửa hai
 * chỗ. Trước redesign, `muted-soft` chỉ đạt 2,58:1 và nằm ở 24 file mà không ai
 * phát hiện — đây là chỗ chặn chuyện đó lặp lại.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { tuongPhan } from "./tuong-phan";

const css = readFileSync(join(__dirname, "../app/globals.css"), "utf8");

/** Giá trị hex của một token; đi theo `var(--khac)` nếu token là bí danh. */
function token(ten: string, sau = 0): string {
  if (sau > 5) throw new Error(`Vòng lặp bí danh ở --${ten}`);
  const m = css.match(new RegExp(`--${ten}:\\s*(#[0-9a-fA-F]{6}\\b|var\\(--([\\w-]+)\\))`));
  if (!m) throw new Error(`Không thấy token --${ten} trong globals.css`);
  return m[2] ? token(m[2], sau + 1) : m[1];
}

/** Chữ trên nền: ≥ 4,5:1. */
const CAP_CHU: [string, string][] = [
  ["ink", "paper"],
  ["ink", "card"],
  ["ink", "sunken"],
  ["ink-2", "paper"],
  ["ink-2", "card"],
  // Nút vô hiệu: chữ `ink-2` trên `sunken` — phải còn đọc được (Review Focus #2).
  ["ink-2", "sunken"],
  ["ink", "accent"],
  ["card", "accent-2"],
  ["accent-2", "card"],
  ["ok", "ok-bg"],
  ["wait", "wait-bg"],
  ["bad", "bad-bg"],
  ["bad", "card"],
  ...[1, 2, 3, 4, 5, 6, 7, 8].map((i): [string, string] => ["ink", `swatch-${i}`]),
  // Token CŨ màn chưa làm lại vẫn dùng — ánh xạ lại phải giữ đạt chuẩn.
  ["muted-soft", "background"],
  ["muted-soft", "surface"],
  ["foreground", "surface"],
  ["background", "primary"], // nút cũ `bg-primary text-white`
  ["primary", "primary-soft"], // mục nav cũ đang chọn
  ["zalo-fg", "zalo-bg"],
  ["facebook-fg", "facebook-bg"],
  ["instagram-fg", "instagram-bg"],
  ["telegram-fg", "telegram-bg"], // cũ: 3,68:1 — trượt
  ["admin-fg", "admin-bg"],
  ["cho-phan-fg", "cho-phan-bg"],
  ["dang-mo-fg", "dang-mo-bg"],
  ["da-dong-fg", "da-dong-bg"],
  ["danger-fg", "danger-bg"],
];

/** Đồ hoạ không phải chữ (viền focus, icon kênh): ≥ 3:1 (WCAG 1.4.11). */
const CAP_DO_HOA: [string, string][] = [
  ["accent-2", "paper"],
  ["accent-2", "card"],
  // Logo kênh xuất hiện trên cả ba nền (thẻ, nền app, đầu bảng/lõm).
  ...["zalo", "facebook", "instagram", "telegram"].flatMap((k) =>
    ["card", "paper", "sunken"].map((nen): [string, string] => [k, nen]),
  ),
];

describe("tương phản token (WCAG AA)", () => {
  it.each(CAP_CHU)("chữ %s trên %s ≥ 4,5:1", (a, b) => {
    expect(tuongPhan(token(a), token(b))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(CAP_DO_HOA)("đồ hoạ %s trên %s ≥ 3:1", (a, b) => {
    expect(tuongPhan(token(a), token(b))).toBeGreaterThanOrEqual(3);
  });

  it("hàm tương phản đúng với mốc chuẩn (đen/trắng = 21:1)", () => {
    expect(tuongPhan("#000000", "#ffffff")).toBeCloseTo(21, 5);
  });

  it("nhận cả hex rút gọn #rgb (trình duyệt trả `#111` cho `#111111`)", () => {
    expect(tuongPhan("#111", "#fff")).toBeCloseTo(tuongPhan("#111111", "#ffffff"), 5);
    expect(Number.isNaN(tuongPhan("#111", "#fbf6e6"))).toBe(false);
  });
});
