import { HopQuanLyMau } from "@/components/mau-tra-loi";

/**
 * `/quan-tri/mau-tra-loi` — Manager (mẫu phòng mình) + Admin (mọi mẫu) (BE-7;
 * layout khu đã chặn Staff). Cùng nội dung với hộp "Quản lý mẫu" trong Hộp thư.
 */
export default function TrangMauTraLoi() {
  return <HopQuanLyMau trang />;
}
