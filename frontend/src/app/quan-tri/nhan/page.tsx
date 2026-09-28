import { HopQuanLyNhan } from "@/components/panel-khach-muc";

/**
 * `/quan-tri/nhan` — Manager + Admin (BE-6: chỉ hai vai này tạo/sửa nhãn; layout
 * khu đã chặn Staff). Cùng nội dung với hộp "Quản lý nhãn" trong Hộp thư.
 */
export default function TrangNhan() {
  return <HopQuanLyNhan trang />;
}
