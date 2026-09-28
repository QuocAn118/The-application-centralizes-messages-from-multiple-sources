# Redesign — Phần 5: Báo cáo (B1–B4) + BE-8 + Recharts

Nguồn: GĐ1 §4.3 (B1–B4), §5 BE-8, §10.1 câu 2 (định nghĩa tỉ lệ phản hồi), §7
(Recharts), X7/X9. Thư viện mới: `recharts` (đã duyệt ở §7; `npm audit` trước/sau
không đổi).

## BE-8 — `GET /analytics/overview?from&to&department_id`

```json
{
  "totals": {"inbound_count", "outbound_count", "opened_count", "closed_count"},
  "avg_first_response_seconds": 1218.4 | null,
  "first_response_samples": 19,
  "response_rate": 0.3 | null,
  "conversations_with_inbound": 10,
  "conversations_replied": 3,
  "daily": [{"date": "2026-09-14", "inbound_count", "outbound_count", "opened_count", "closed_count"}]
}
```

- **Tỉ lệ phản hồi** (chốt §10.1 (a)): hội thoại có ≥1 tin trả lời / hội thoại có
  ≥1 tin vào, **cả hai trong kỳ**. Đếm HỘI THOẠI phân biệt — rollup chỉ đếm tin nên
  đọc thẳng #1 qua port mới `IResponseRateSource` (implementation trên
  `InboxStatsSource`): ngày = ngày địa phương của từng tin, phòng = phòng HIỆN TẠI
  (cùng quy tắc backfill GĐ2/GĐ3). `null` khi kỳ không có tin vào (khác 0%).
- **Phản hồi đầu TB có trọng số**: tổng giây / tổng mẫu của cả khoảng (rollup
  agent), không trung bình các trung bình.
- `daily` đủ mọi ngày trong khoảng, ngày trống = 0.
- Phạm vi như 4 báo cáo khác (RB-4): Manager ép phòng mình, Staff 403.
- Test: unit (trọng số 70 ≠ 80, ép phạm vi, null), integration SQL (00:30 VN,
  trả lời ngoài kỳ, chỉ tin ra, chưa phân phòng), e2e qua webhook thật.

## Giao diện

- **Khung chung**: DauTrang theo tab + **B3** nút nhanh 7 ngày · 30 ngày · Tháng
  này · Tháng trước (`aria-pressed`, bật đúng nút khớp khoảng hiện tại) + hai ô
  ngày (giữ) + ô phòng chỉ Admin.
- **B1 Hội thoại**: 4 thẻ (Tin vào · Tỉ lệ phản hồi kèm "x/y hội thoại" · Phản
  hồi đầu TB kèm số mẫu · Đã đóng) → biểu đồ cột Tin vào/Tin ra theo ngày
  (Recharts; SVG `aria-hidden` + bảng `sr-only` cùng số liệu; chữ chú giải màu
  mực vì chữ vàng trên nền kem không đạt tương phản) → bảng chi tiết (phòng, kênh).
- **B2**: dòng có tin vào mà 0 tin ra → nền cảnh báo + icon + "n tin vào, chưa có
  tin trả lời nào" (không chỉ dựa vào màu).
- **B4**: thẻ tóm tắt tính từ dữ liệu đã tải, không gọi thêm API.
  - Nhân viên: Đã xử lý · Được gán tự động · Nhân viên có hoạt động. (Không có thẻ
    phản hồi TB nhóm: báo cáo không trả số mẫu từng người → gộp sẽ sai; số đúng ở
    tab Hội thoại.)
  - Ca & KPI: Tổng số ca · Tổng giờ công · Đạt KPI "x/y" (chỉ trên người CÓ mục
    tiêu; null ≠ chưa đạt). Cột %KPI có thanh tiến độ như màn KPI (null không vẽ).
  - Đơn từ: Tổng đơn · Đang chờ duyệt · Thời gian duyệt TB (có trọng số theo số đơn).

## Dữ liệu dev / kịch bản

- `gieo_hop_thu_2a.py` ghi thẳng DB (bỏ qua hook rollup) → nay gọi
  `POST /analytics/rollups/rebuild` các ngày vừa gieo để báo cáo khớp nguồn.
- Kịch bản mới `ui-p5.mjs`: số trên thẻ đối chiếu với CHÍNH phản hồi API trang nhận.
- `ui-f5-gd1` cập nhật selector (đổi UI có chủ đích): kiểm bảng có tên "Chi tiết
  theo phòng và kênh" thay vì "bảng duy nhất trên trang".
