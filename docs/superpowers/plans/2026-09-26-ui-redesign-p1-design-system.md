# Phần 1 — Design system Neo-Brutalism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Token + bộ component gốc Neo-Brutalism + khung app + trang `/design-system` (dev), không sửa file màn nào.

**Architecture:** Token Tailwind v4 trong `globals.css` (`@theme inline`), token cũ ánh xạ lại để màn chưa làm không vỡ. Component mới ở `components/ui/`, mỗi file một việc. Component dùng chung cũ (`HopThoai`, `NutChinh`…) giữ nguyên API, đổi ruột sang component mới → 15 hộp thoại đổi theo mà không sửa file gọi.

**Tech Stack:** Next.js 16.3, React 19.2, Tailwind v4, vitest (env `node` — không render component), lucide-react, @radix-ui/react-dialog / -dropdown-menu / -tooltip.

**Spec:** `docs/superpowers/specs/2026-09-26-ui-redesign-p1-design-system.md`

## Global Constraints

- Chỉ desktop; khung app `min-width: 1280px`, hẹp hơn thì cuộn ngang.
- Bo góc **một giá trị `6px`**; viền `2px ink` (nút chính `3px`); bóng `4px 4px 0 #111`.
- **Có bóng = bấm được.** Badge và phần tử tĩnh không bóng.
- Bên trong bảng/lịch/danh sách: kẻ `1px line`, không viền dày.
- Mọi chữ ≥ 4,5:1; focus `3px accent-2` offset `2px` qua `:focus-visible`.
- Icon chỉ từ lucide-react. Không SVG vẽ tay, không emoji.
- Chữ mới không dùng `—`. `DAU_GACH` giữ nguyên (chờ user quyết).
- Hiển thị "Cấu hình", không "Quản trị". Route `/quan-tri` giữ.
- **Không sửa** `components/*/man-*.tsx`, `bang-*.tsx`, `app/**/page.tsx` (trừ `/design-system`).

## Review Focus

1. **Hộp thoại `onDong={null}`** (bước hiện mật khẩu tạm): Esc / bấm nền / nút × phải **không** đóng được → kiểm bằng Playwright ở trang design-system (Task 10).
2. **Nút vô hiệu** phải trông "không bấm được" nhưng vẫn đọc được chữ (không mờ tới mức như lỗi) → kiểm ảnh chụp + test tương phản `ink-2` trên `sunken`.
3. **Focus bàn phím** thấy được trên nút, ô nhập, tab, mục menu → chụp sau khi nhấn Tab (Task 10).
4. **`/design-system` lọt ra production** → `next start` phải trả 404 (Task 10).
5. **Kịch bản kiểm chứng cũ** dựa vào `role="dialog"`, `aria-current="page"`, chữ nút ("Lưu", "Thêm từ khoá") → chạy lại toàn bộ (Task 10).

---

### Task 1: Thư viện + token + test tương phản

**Files:**
- Modify: `frontend/package.json` (qua npm), `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx`
- Test: `frontend/src/lib/tuong-phan.test.ts`

**Interfaces:**
- Produces: lớp Tailwind `bg-paper bg-card bg-sunken text-ink text-ink-2 border-ink border-line bg-accent bg-accent-2 text-accent-2 text-ok bg-ok-bg text-wait bg-wait-bg text-bad bg-bad-bg text-zalo text-facebook text-instagram text-telegram bg-swatch-1..8 shadow-nb shadow-nb-sm rounded-nb`.

- [ ] **Step 1: Cài thư viện**
  `cd frontend && npm install lucide-react @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tooltip`
- [ ] **Step 2: Viết test tương phản đọc hex từ `globals.css` (đỏ vì token chưa có)**

```ts
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(join(__dirname, "../app/globals.css"), "utf8");
function token(ten: string): string {
  const m = css.match(new RegExp(`--${ten}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`Không thấy token --${ten}`);
  return m[1];
}
function doSang(hex: string): number { /* WCAG relative luminance */ }
function tuongPhan(a: string, b: string): number { /* (L1+.05)/(L2+.05) */ }

const CAP_CHU: [string, string][] = [
  ["ink","paper"],["ink","card"],["ink","sunken"],["ink-2","paper"],["ink-2","card"],
  ["ink-2","sunken"],["ink","accent"],["card","accent-2"],["accent-2","card"],
  ["ok","ok-bg"],["wait","wait-bg"],["bad","bad-bg"],
  ...[1,2,3,4,5,6,7,8].map((i) => ["ink", `swatch-${i}`] as [string,string]),
];
const CAP_DO_HOA: [string, string][] = [
  ["accent-2","paper"],["zalo","card"],["facebook","card"],["instagram","card"],["telegram","card"],
];
describe("tương phản token (WCAG AA)", () => {
  it.each(CAP_CHU)("chữ %s trên %s ≥ 4,5:1", (a, b) =>
    expect(tuongPhan(token(a), token(b))).toBeGreaterThanOrEqual(4.5));
  it.each(CAP_DO_HOA)("đồ hoạ %s trên %s ≥ 3:1", (a, b) =>
    expect(tuongPhan(token(a), token(b))).toBeGreaterThanOrEqual(3));
});
```

- [ ] **Step 3: Chạy** `npx vitest run src/lib/tuong-phan.test.ts` → FAIL "Không thấy token --paper"
- [ ] **Step 4: Viết token** trong `:root` (giá trị §3.1 spec) + `@theme inline` (`--color-*`, `--shadow-nb: 4px 4px 0 var(--ink)`, `--shadow-nb-sm: 2px 2px 0 var(--ink)`, `--radius-nb: 6px`); ánh xạ token cũ theo §3.3; `body { background: var(--paper) }`; khối `:focus-visible { outline: 3px solid var(--accent-2); outline-offset: 2px }`; `@media (prefers-reduced-motion: reduce) { * { transition: none !important } }`. `layout.tsx`: thêm weight `"800"`, `<body className="min-w-[1280px] ...">`, sửa `metadata` (bỏ `—`, thêm Telegram).
- [ ] **Step 5: Chạy lại** → PASS 25 test. `npx tsc --noEmit` sạch.
- [ ] **Step 6: Commit** `feat(ui): token Neo-Brutalism + test tuong phan`

### Task 2: Bảng 8 màu + `mauTuId`

**Files:** Create `frontend/src/components/ui/ban-mau.ts`; Test `frontend/src/components/ui/ban-mau.test.ts`

**Interfaces:** Produces `BAN_MAU: readonly string[]` (8 lớp `bg-swatch-N`), `mauTuId(id: string): number` (1..8, ổn định).

- [ ] **Step 1: Test** — cùng id → cùng số; mọi kết quả trong 1..8; 200 id ngẫu nhiên phủ ≥ 6/8 màu; chuỗi rỗng không ném lỗi.
- [ ] **Step 2: FAIL** → **Step 3:** hash FNV-1a 32-bit `% 8 + 1` → **Step 4: PASS** → **Step 5: Commit**

### Task 3: `Nut`, `NutIcon`, `GoiY` + nối `NutChinh`/`NutPhu`

**Files:** Create `components/ui/nut.tsx`, `components/ui/nut-icon.tsx`, `components/ui/goi-y.tsx`; Modify `components/hop-thoai.tsx` (chỉ phần `NutChinh`/`NutPhu`)

**Interfaces:**
- Produces: `Nut({ bienThe?: "chinh"|"phu"|"nguyHiem"|"trong", co?: "sm"|"md", icon?: LucideIcon, dangChay?: boolean, ...ButtonHTMLAttributes })`; `NutIcon({ icon: LucideIcon, nhan: string, bienThe?, co?, ...})`; `GoiY({ noiDung: string, children })`; `NutChinh`/`NutPhu` giữ API cũ (`nguyHiem`).

- [ ] **Step 1:** Lớp chung: `inline-flex items-center gap-2 rounded-nb border-2 border-ink font-semibold transition-[transform,box-shadow] duration-100 shadow-nb-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:border-dashed disabled:bg-sunken disabled:text-ink-2 disabled:shadow-none disabled:translate-0 disabled:cursor-not-allowed whitespace-nowrap`. `chinh`: `bg-accent text-ink border-[3px] shadow-nb hover:shadow-nb-sm`. `phu`: `bg-card text-ink`. `nguyHiem`: `bg-card text-bad border-bad`. `trong`: không viền, không bóng, `hover:bg-sunken`. `dangChay` → `aria-busy`, icon `Loader2 animate-spin`, `disabled`.
- [ ] **Step 2:** `NutIcon` bắt buộc `nhan` (aria-label) và bọc `GoiY`. `GoiY` = Radix Tooltip (`Provider` delay 300ms) nền `ink` chữ `card`, `rounded-nb`.
- [ ] **Step 3:** `NutChinh` → `<Nut bienThe={nguyHiem ? "nguyHiem" : "chinh"} {...props} />`; `NutPhu` → `<Nut bienThe="phu" {...props} />`. Giữ `type="button"` mặc định.
- [ ] **Step 4:** `tsc` + `eslint` sạch; `npm test` giữ 247+ xanh.
- [ ] **Step 5: Commit** `feat(ui): Nut, NutIcon, GoiY; NutChinh/NutPhu dung Nut`

### Task 4: Ô nhập + `Truong`

**Files:** Create `components/ui/o-nhap.tsx`, `components/ui/truong.tsx`

**Interfaces:** `ONhap`, `VungNhap`, `OChon` = input/textarea/select có `forwardRef`, prop `coLoi?: boolean` (viền `bad` + `aria-invalid`). `Truong({ nhan, goiY?, loi?, children: (idProps: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => ReactNode })`.

- [ ] **Step 1:** Lớp ô: `w-full rounded-nb border-2 border-ink bg-card px-3 py-2 text-sm text-ink placeholder:text-ink-2 disabled:border-dashed disabled:bg-sunken`. `OChon` thêm `appearance-none` + icon `ChevronDown` lucide đặt tuyệt đối.
- [ ] **Step 2:** `Truong`: nhãn `text-sm font-semibold` trên, gợi ý `text-xs text-ink-2`, lỗi `text-xs font-semibold text-bad` dưới, `useId` nối `aria-describedby`.
- [ ] **Step 3:** `tsc` + `eslint` → **Step 4: Commit**

### Task 5: `The`, `DauTrang`, `TabKhu`; 4 `Tab*` dùng `TabKhu`; "Cấu hình"

**Files:** Create `components/ui/the.tsx`, `components/ui/dau-trang.tsx`, `components/ui/tab-khu.tsx`; Modify `components/tab-nhan-su.tsx`, `tab-quan-tri.tsx`, `tab-tu-khoa.tsx`, `tab-bao-cao.tsx`, `lib/i18n.ts` (chuỗi "Quản trị")

**Interfaces:** `The({ children, className? })`, `TheDau({ tieuDe, moTa?, hanhDong? })`; `DauTrang({ tieuDe, moTa?, hanhDong? })`; `TabKhu({ tieuDe: string, tab: { duongDan: string; nhan: string }[] })` — giữ `aria-current="page"` và `nav[aria-label]`.

- [ ] **Step 1:** Grep mọi chuỗi hiển thị "Quản trị" trong `i18n.ts` → đổi thành "Cấu hình" (giữ nhãn vai `vai.ADMIN` = "Quản trị viên"? → **giữ**: đó là tên vai, không phải tên khu).
- [ ] **Step 2:** `TabKhu`: header `bg-card border-b-2 border-ink`, tiêu đề 28/800, tab là link `border-2 border-ink rounded-nb` khi đang chọn `bg-accent shadow-nb-sm`, còn lại không viền; giữ đúng DOM `header > nav[aria-label] > a[aria-current]`.
- [ ] **Step 3:** Mỗi `Tab*.tsx` còn lại: danh sách tab + điều kiện vai của riêng nó (TabQuanTri giữ lọc `riengAdmin`) rồi gọi `TabKhu`.
- [ ] **Step 4:** `tsc` + `npm test` (test quyền tab không đổi) → **Step 5: Commit**

### Task 6: `HuyHieu`, `Bang`, `Avatar`, `IconKenh`; nối `badges.tsx`

**Files:** Create `components/ui/huy-hieu.tsx`, `bang.tsx`, `avatar.tsx`, `icon-kenh.tsx`; Modify `components/badges.tsx`

**Interfaces:** `HuyHieu({ tong?: "trung"|"ok"|"wait"|"bad"|"info", children })`; `Bang`, `Th`, `Td`, `Tr` (bọc thẻ HTML, lớp mặc định); `Avatar({ id: string, ten: string|null, kenh?: Platform, co?: "sm"|"md" })`; `IconKenh({ kenh: Platform, co?: number })`.

- [ ] **Step 1:** Kiểm lucide có glyph nào cho kênh: `node -e "const l=require('lucide-react');console.log(['Facebook','Instagram','Send','MessageCircle'].map(n=>n+':'+!!l[n]))"`. Chốt map theo kết quả (thiếu logo thương hiệu thì dùng glyph chung + màu + `title`).
- [ ] **Step 2:** `HuyHieu`: `rounded-nb border-2 px-2 py-0.5 text-xs font-semibold` **không bóng**; tông → cặp màu nền/chữ/viền cùng tông. `Bang`: khung `border-2 border-ink rounded-nb shadow-nb overflow-hidden`; `Th` `bg-sunken text-xs font-bold uppercase text-ink-2`; `Tr` `border-t border-line`.
- [ ] **Step 3:** `badges.tsx`: `BadgeKenh` = `IconKenh` + tên; `BadgeTrangThai` = `HuyHieu` tông theo trạng thái. Giữ export cũ.
- [ ] **Step 4:** `tsc` + `npm test` (test nhãn kênh phủ đủ 4 nền tảng vẫn xanh) → **Step 5: Commit**

### Task 7: `HopThoai` → Radix Dialog (giữ API)

**Files:** Modify `components/hop-thoai.tsx`, `components/hop-xac-nhan.tsx`

**Interfaces:** Không đổi: `HopThoai({ tieuDe, moTa?, loi?, onDong: (() => void) | null, children?, chanDuoi })`.

- [ ] **Step 1:** `<Dialog.Root open onOpenChange={(mo) => { if (!mo) onDong?.(); }}>` + `Portal` + `Overlay` (`fixed inset-0 bg-ink/40`) + `Content` (`rounded-nb border-2 border-ink bg-card shadow-nb p-6 max-w-[480px]`). `onDong === null` → `onEscapeKeyDown`/`onPointerDownOutside`/`onInteractOutside` gọi `e.preventDefault()`, không render `Dialog.Close`.
- [ ] **Step 2:** Giữ `role="dialog"` (Radix tự đặt), `aria-labelledby` qua `Dialog.Title`, `moTa` qua `Dialog.Description` (không có mô tả → `aria-describedby={undefined}` để Radix khỏi cảnh báo). Nút × = `NutIcon icon={X} nhan={t("chung.dong")}`. Lỗi = khung `bg-bad-bg border-2 border-bad`.
- [ ] **Step 3:** `tsc` + `eslint` + `npm test` → **Step 4: Commit**

### Task 8: `MenuHanhDong`, trạng thái tải/rỗng/lỗi; restyle `ThanhPhanTrang`, `OTimKiem`, `ChanTheoVai`

**Files:** Create `components/ui/menu-hanh-dong.tsx`, `components/ui/trang-thai.tsx`; Modify `thanh-phan-trang.tsx`, `o-tim-kiem.tsx`, `chan-theo-vai.tsx`

**Interfaces:** `MenuHanhDong({ nhan: string, muc: { nhan: string; icon?: LucideIcon; nguyHiem?: boolean; onChon: () => void; an?: boolean }[] })` — mục `nguyHiem` tự dời xuống cuối, ngăn bằng `Separator`. `TrangThaiTai({ dong?: number })` (khung xương), `TrangThaiRong({ icon, tieuDe, moTa?, hanhDong? })`, `TrangThaiLoi({ thongDiep, onThuLai? })`.

- [ ] **Step 1–3:** Viết, dùng `NutIcon icon={MoreHorizontal}` làm trigger; `ChanTheoVai` dùng `TrangThaiLoi` (giữ câu "không có quyền" — kịch bản kiểm chứng tìm chuỗi này).
- [ ] **Step 4:** `tsc` + `eslint` + `npm test` → **Step 5: Commit**

### Task 9: `NavRail` lucide + khung app

**Files:** Modify `components/nav-rail.tsx`

- [ ] **Step 1:** Thay 6 `Icon*` vẽ tay bằng lucide (`MessagesSquare`, `Users`, `Tags`, `BarChart3`, `Settings`, `LogOut`). Nền `bg-card border-r-2 border-ink`; mục đang ở: `bg-accent border-2 border-ink shadow-nb-sm`; mục khoá: `text-ink-2` + icon `Lock` nhỏ + tooltip lý do. Giữ `href`, `aria-current="true"` và điều kiện vai như cũ.
- [ ] **Step 2:** Grep còn `<svg` viết tay trong `components/` ngoài file màn → chỉ còn ở file màn (Phần sau xử lý).
- [ ] **Step 3:** `tsc` + `eslint` + `npm test` → **Step 4: Commit**

### Task 10: Trang `/design-system` + kiểm chứng toàn bộ

**Files:** Create `frontend/src/app/design-system/page.tsx` (+ `components/ui/trang-mau.tsx` client nếu cần state)

- [ ] **Step 1:** `page.tsx`: `if (process.env.NODE_ENV === "production") notFound();` rồi hiện đủ mục §5 spec. Không bọc `AuthGuard` (trang dev, không cần đăng nhập để duyệt).
- [ ] **Step 2:** `npm test` + `tsc` + `eslint` + `next build`.
- [ ] **Step 3:** `next start` → `curl /design-system` phải **404**; `next dev -p 3001` (dev) → trang hiện.
- [ ] **Step 4:** Chạy lại kịch bản cũ (`ui-f5-gd1/gd2`, `ui-f4-gd1/gd2`, `ui-f4-no`, `ui-f3-gd1/2/3`) trên bản build mới. Hỏng vì đổi UI có chủ đích → sửa selector + ghi lý do.
- [ ] **Step 5:** Playwright MCP 1440px: chụp toàn trang design-system; nhấn Tab tới nút/ô nhập/tab rồi chụp focus; mở hộp thoại `onDong={null}` → nhấn Esc + bấm nền → phải còn mở. Chụp 2–3 màn hiện có ("nửa cũ nửa mới"). **Tự xem từng ảnh.**
- [ ] **Step 6: Commit** `feat(ui): trang /design-system (chi dev)`; dừng, báo user.
