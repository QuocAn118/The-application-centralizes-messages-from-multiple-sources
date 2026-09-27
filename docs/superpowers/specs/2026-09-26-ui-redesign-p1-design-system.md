# Redesign Phần 1 — Design system Neo-Brutalism + khung app

Nguồn: [GĐ1 rà soát UX](2026-09-26-ui-redesign-gd1-ra-soat-ux.md) (đã duyệt).
Nhánh: `feat/ui-design-system`.

## 1. Mục tiêu & ranh giới

Tạo **token + bộ component gốc + khung app** theo Neo-Brutalism, và một trang
`/design-system` (chỉ môi trường dev) để duyệt. **Dừng ở đó** chờ user duyệt.

**Được sửa:** `globals.css`, `layout.tsx`, `components/ui/*` (mới), và các
component **dùng chung** đã có (`hop-thoai`, `hop-xac-nhan`, `nav-rail`,
`tab-*`, `thanh-phan-trang`, `o-tim-kiem`, `badges`, `chan-theo-vai`).

**KHÔNG sửa:** bất kỳ file màn nào (`components/*/man-*.tsx`, `bang-*.tsx`,
`app/*/page.tsx` ngoài `/design-system`), logic, API, backend.

Hệ quả phải chấp nhận: sau Phần 1, các màn sẽ trông **nửa cũ nửa mới** (khung
app, hộp thoại, tab đã mới; thân màn còn cũ) cho tới khi Phần 2–7 làm tới. Để
nửa cũ không vỡ, token cũ (`--primary`, `--muted-soft`…) được **ánh xạ lại** sang
giá trị mới an toàn tương phản, không xoá (§3.3).

## 2. Design read & dial (taste-skill)

*Công cụ vận hành nội bộ, dùng cả ngày, cho nhân viên CSKH và quản lý người Việt;
ngôn ngữ Neo-Brutalism, tiết chế cho màn nhiều dữ liệu; Tailwind v4 token + Radix
primitive + lucide.*

`DESIGN_VARIANCE 3` (bố cục dễ đoán) · `MOTION_INTENSITY 2` (chỉ phản hồi nhấn) ·
`VISUAL_DENSITY 6` (khá dày, kẻ 1px bên trong).

## 3. Token

### 3.1 Màu (đã kiểm bằng script: 26/26 cặp đạt)

| Token | Giá trị | Dùng cho | Tương phản |
|---|---|---|---|
| `paper` | `#FBF6E6` | Nền app (kem) | — |
| `card` | `#FFFDF6` | Nền thẻ, ô nhập (ngà, không trắng tinh) | — |
| `sunken` | `#F3ECD6` | Đầu bảng, vùng lõm, nút phụ khi rê | — |
| `ink` | `#111111` | Chữ chính, **mọi viền dày**, bóng | 17,5:1 trên `paper` |
| `ink-2` | `#4E4A40` | Chữ phụ (thay `muted-soft` 2,58:1) | 8,2:1 |
| `line` | `#D8CFB5` | Kẻ mảnh 1px **bên trong** bảng/lịch/danh sách | (trang trí) |
| `accent` | `#FFD43B` | **Màu chính**: nút chính, chọn đang mở, hôm nay | chữ `ink` 13,3:1 |
| `accent-2` | `#1F4FD8` | **Màu phụ**: link, viền focus, mục đang chọn | trên `card` 6,5:1 |
| `ok` / `ok-bg` | `#146C2E` / `#DDF3E2` | Thành công | 5,6:1 |
| `wait` / `wait-bg` | `#7A4B00` / `#FFEDB8` | Chờ xử lý | 6,4:1 |
| `bad` / `bad-bg` | `#A8201A` / `#FCE1DD` | Lỗi, huỷ hoại | 5,9:1 |
| `zalo` `facebook` `instagram` `telegram` | `#0068FF` `#1877F2` `#C13584` `#1C8AC4` | **Chỉ icon nhỏ** | ≥ 3:1 (đồ hoạ) |

**Bảng 8 màu dịu** `swatch-1..8` (`#FFD9A8 #FFC2C7 #C9E7FF #CDEFC8 #E5D4FF #FFF0A6
#BFEDE6 #E9DCC9`), chữ `ink` trên mọi màu ≥ 12:1. Dùng chung cho: **màu nhãn
(BE-6, chỉ chọn trong bảng này)**, màu ca làm việc, nền avatar. Màu suy ổn định từ
id (`mauTuId(id) → 1..8`).

Test khoá: `lib/tuong-phan.test.ts` đọc hex **từ `globals.css`** rồi kiểm từng cặp
trên. Đổi màu làm tụt dưới ngưỡng thì test đỏ.

### 3.2 Hình, bóng, chữ, chuyển động

- **Viền:** `2px solid ink` cho thẻ, nút, ô nhập, tab, badge. Nút chính `3px`.
- **Bo góc: một giá trị duy nhất `6px`** cho mọi thứ (kể cả avatar — avatar vuông
  bo 6px, không tròn). Ngoại lệ duy nhất: chấm trạng thái tròn.
- **Bóng cứng:** `--shadow: 4px 4px 0 ink`, `--shadow-sm: 2px 2px 0 ink`.
  - **Quy tắc bóng (sửa sau duyệt Phần 1 cho khớp thực tế).** Bóng có BA vai
    trò, phân biệt bằng cỡ bóng và việc có phản hồi hay không:
    1. **Nút** = bóng NHỎ (`2px`; nút chính `4px`) **+ phản hồi**: rê dịch 2px,
       nhấn dịch hết và bóng về 0. Bóng + phản hồi = bấm được.
    2. **Card / bảng / khung** (thẻ, bảng, hộp thoại, menu, đầu khu) = bóng
       `4px` **làm khung**, KHÔNG phản hồi. Nó đánh dấu "khối nổi" của trang,
       không phải thứ để bấm.
    3. **Huy hiệu** (và mọi nhãn trạng thái) = **KHÔNG bóng**. Đây là cách giải
       I/S6 ("Đang dùng" trông như nút).
  - Bản đầu viết gọn "có bóng = bấm được" là sai với chính thiết kế (card cũng
    có bóng mà không bấm được) — đã thay bằng ba quy tắc trên.
  - Nút: rê → dịch `2px,2px` + bóng `2px`; nhấn → dịch `4px,4px` + bóng `0`.
  - Thẻ khung ngoài (card, header): bóng `4px`. **Bên trong** bảng/lịch/danh sách:
    chỉ kẻ `1px line`, không viền dày, không bóng.
- **Chữ:** Be Vietnam Pro 400/500/600/700/**800** (thêm 800).
  Tiêu đề trang 28/800 · tiêu đề mục 18/700 · nội dung 14/400–500 · nhỏ 12/600.
  Số: `tabular-nums`.
- **Focus:** `outline: 3px solid accent-2; outline-offset: 2px` qua
  `:focus-visible` cho mọi phần tử tương tác (X3).
- **Chuyển động:** chỉ `transform` + `box-shadow`, 100 ms. Tắt dịch chuyển dưới
  `prefers-reduced-motion: reduce`.
- **Khung app:** `min-width: 1280px`, hẹp hơn thì cuộn ngang (quyết định #6).

### 3.3 Ánh xạ token cũ (để màn chưa làm không vỡ)

| Token cũ | → Giá trị mới | Lý do |
|---|---|---|
| `background`, `surface` | `paper` / `sunken` | Nền kem toàn app ngay |
| `foreground` | `ink` | |
| `border` | `line` | Kẻ mảnh bên trong giữ nguyên vai trò |
| `muted`, `muted-soft` | `ink-2` | **Sửa luôn X2** (2,58:1 → 8,2:1) trên mọi màn |
| `primary` | `accent-2` (cobalt) | Nút cũ `bg-primary text-white` vẫn đạt 6,5:1. **Không** đổi thẳng sang vàng: chữ trắng trên vàng chỉ ~1,3:1 |
| `primary-soft` | `#E4EAFB` | |
| `danger-*`, `dang-mo-*`, `cho-phan-*` | `bad` / `ok` / `wait` | |
| kênh `*-fg` | màu kênh mới | Telegram 3,68:1 → đạt |

## 4. Component (`components/ui/`)

Mỗi component một file, API tiếng Việt như phần còn lại của repo.

| Component | Nội dung | Ghi chú |
|---|---|---|
| `nut.tsx` → `Nut` | biến thể `chinh` (vàng, viền 3px) · `phu` (ngà) · `nguyHiem` (chữ/viền `bad`) · `trong` (không viền, dùng trong menu/thanh công cụ); cỡ `sm`/`md`; `dangChay`; icon trái | Vô hiệu: nền `sunken`, viền đứt, **không bóng**, chữ `ink-2` — không nhạt như lỗi (X8) |
| `nut-icon.tsx` → `NutIcon` | nút vuông chỉ icon, **bắt buộc** `nhan` (aria-label + tooltip) | |
| `o-nhap.tsx` → `ONhap`, `VungNhap`, `OChon` | input / textarea / **select native** có style | Select native: bàn phím + đọc màn hình sẵn, không cần Radix Select (ponytail) |
| `truong.tsx` → `Truong` | nhãn trên, gợi ý, lỗi dưới ô (taste §4.6) | nối `aria-describedby` |
| `the.tsx` → `The`, `TheDau` | thẻ khung ngoài 2px + bóng; đầu thẻ có tiêu đề + chỗ đặt nút | |
| `dau-trang.tsx` → `DauTrang` | tiêu đề trang 28/800 + mô tả + nút chính bên phải (X6, X7) | |
| `tab-khu.tsx` → `TabKhu` | thanh tab khu (link), thay 4 `Tab*` chép nhau (X10) | Giữ `aria-current="page"` như cũ (kịch bản kiểm chứng dựa vào) |
| `huy-hieu.tsx` → `HuyHieu` | tông `trung` / `ok` / `wait` / `bad` / `info`; **không bóng**; chữ 12px | |
| `bang.tsx` → `Bang`, `Th`, `Td`, `Tr` | viền dày chỉ ở khung ngoài, kẻ 1px bên trong, đầu bảng `sunken` | |
| `menu-hanh-dong.tsx` → `MenuHanhDong` | nút "⋯" + Radix DropdownMenu; mục `nguyHiem` luôn xếp **cuối**, cách bằng vạch | X5 |
| `goi-y.tsx` → `GoiY` | Radix Tooltip | |
| `avatar.tsx` → `Avatar` | vuông bo 6px, màu `mauTuId`, chữ cái đầu; icon kênh nhỏ gắn góc | I1, I3 |
| `icon-kenh.tsx` → `IconKenh` | icon lucide + màu kênh | Lucide **không có** logo Zalo/Telegram (không có logo thương hiệu nào). Dùng glyph chung + màu kênh + `title`; xem §7 |
| `trang-thai.tsx` → `TrangThaiTai`, `TrangThaiRong`, `TrangThaiLoi`, `KhungXuong` | tải (khung xương theo hình dạng thật) / rỗng (icon + câu + nút) / lỗi (thông điệp server + "Thử lại") | X9 |
| `ban-mau.ts` → `BAN_MAU`, `mauTuId` | 8 màu dịu + hàm suy màu ổn định | có test |

**Component dùng chung đã có — đổi ruột, giữ nguyên API:**
- `HopThoai` → Radix Dialog. Giữ `onDong={null}` = không đóng được (chặn Esc +
  bấm nền, ẩn nút ×). Được thêm: bẫy focus, trả focus về nút mở.
- `NutChinh` / `NutPhu` → bọc `Nut`. 15 hộp thoại đổi theo mà không sửa file nào.
- `HopXacNhan`, `ThanhPhanTrang`, `OTimKiem`, `badges` → đổi style qua component mới.
- `NavRail` → lucide, khung mới; `Tab*` (4 file) → gọi `TabKhu`, xoá phần chép.
- Mọi chữ hiển thị "Quản trị" → **"Cấu hình"** (X11). Route `/quan-tri` giữ nguyên.

## 5. Trang `/design-system`

`app/design-system/page.tsx`. **Chỉ dev:** `if (process.env.NODE_ENV ===
"production") notFound()` — bản build production trả 404.

Hiện đủ: bảng màu kèm tỉ lệ tương phản, bảng 8 màu, thang chữ (có câu tiếng Việt
đủ dấu: *"Quý khách đã được chuyển sang phòng Kỹ thuật lúc 14:32"*), mọi biến thể
và trạng thái nút (thường / rê / nhấn / focus / vô hiệu / đang chạy), ô nhập (có
lỗi), badge, bảng mẫu, menu "⋯", tooltip, hộp thoại, avatar + icon kênh, 3 trạng
thái tải/rỗng/lỗi, đầu trang + tab khu.

## 6. Kiểm chứng (điều kiện xong)

1. `npm test` (có thêm test tương phản + `mauTuId`), `tsc`, `eslint`, `next build`.
2. **Kịch bản cũ vẫn qua:** `ui-f5-gd1/gd2`, `ui-f4-gd1/gd2`, `ui-f4-no`
   (và các kịch bản #F3 còn chạy được). Hỏng vì đổi selector/chữ có chủ đích thì
   sửa kịch bản + ghi lý do (quy tắc 10.7).
3. Playwright MCP chụp `/design-system` ở 1440px, **tự xem ảnh**: dấu tiếng Việt,
   tương phản, focus thấy được (chụp trạng thái focus bằng bàn phím).
4. Chụp thêm 2–3 màn hiện có để user thấy trạng thái "nửa cũ nửa mới" (không phải
   để duyệt màn, chỉ để không bất ngờ).

## 6b. Quyết định sau duyệt Phần 1 (2026-09-27)

- Không làm dark mode. Giữ `—` (`DAU_GACH`) cho ô chưa có số liệu.
- Badge vai Admin: **"Quản trị viên"**.
- Icon kênh: **logo thương hiệu thật** từ gói `simple-icons` (có cả Zalo). Màu
  chính thức; riêng Telegram `#26A5E4` trượt 3:1 nên làm đậm `#1C8AC4`.
- **Cỡ chữ tối thiểu 12px toàn app**, khoá bằng `lib/co-chu-toi-thieu.test.ts`.
- Quy tắc bóng viết lại (§3.2).
- Từ Phần 2a: **không dùng taste-skill**; frontend-design nếu cần; đặc tả
  Neo-Brutalism vẫn là chuẩn.

## 7. Chỗ taste-skill ngược đặc tả (theo đặc tả, báo user)

| taste-skill nói | Đặc tả / quyết định user | Làm theo |
|---|---|---|
| Skill này **không dành cho dashboard/admin**, nên dùng Fluent/Carbon (§13) | Neo-Brutalism tự dựng | Đặc tả. Chỉ lấy các nguyên tắc chung: tương phản, khoá hình dạng, khoá màu, đủ trạng thái, nhãn trên ô nhập |
| Bóng phải nhuộm theo nền, **cấm bóng đen** trên nền sáng (§4.4) | Bóng cứng `#111` | Đặc tả |
| **Cấm nền kem** kiểu `#faf7f1`… (§4.2) | Nền kem/trắng ngà | Đặc tả. (Luật đó cho web tiêu dùng cao cấp; `#FBF6E6` cũng không nằm trong danh sách cấm) |
| lucide "không khuyến khích" (§3.C) | User chọn lucide | lucide (skill cho phép khi user yêu cầu) |
| **Bắt buộc dark mode** (§6.C) | Không nhắc | **Không làm** ở Phần 1. Hỏi user |
| Cấm hoàn toàn dấu `—` (§9.G) | — | Chữ mới không dùng `—`. **Nhưng** `DAU_GACH = "—"` là quy ước "chưa có số liệu" trong bảng, đã khoá bằng test null-vs-0 ở #F3–#F5 → **giữ**, hỏi user |
| Cấm "eyebrow" chữ hoa giãn chữ (§4.7) | — | Luật cho landing page. Đầu cột bảng chữ hoa vẫn giữ (đó là nhãn cột, không phải eyebrow) |
| Lucide không có logo thương hiệu | "Mỗi kênh một màu, chỉ dùng ở icon nhỏ" | Glyph chung (`MessageCircle`/`Send`/`Camera`/`Facebook`?) + màu kênh; xem ảnh để chốt. Không vẽ SVG tay (cấm cả trong brief lẫn skill) |

## 8. Thư viện thêm

| Gói | Lý do |
|---|---|
| `lucide-react` | Bộ icon duy nhất (quyết định #4); thay 9 SVG vẽ tay |
| `@radix-ui/react-dialog` | Bẫy focus, trả focus, Esc, ARIA cho 15 hộp thoại |
| `@radix-ui/react-dropdown-menu` | Menu "⋯" điều hướng bàn phím đúng chuẩn |
| `@radix-ui/react-tooltip` | Tên cho nút chỉ-icon (bắt buộc cho `NutIcon`) |

Không thêm: Radix Select/Tabs (select native đủ; tab khu là link), Radix Popover
(chưa cần — thêm ở Phần 2a cho chọn người phụ trách), shadcn (§7 GĐ1).
