import { HopQuanLyMau } from "@/components/mau-tra-loi";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Mẫu trả lời" };

/**
 * `/quan-tri/mau-tra-loi` — Manager (mẫu phòng mình) + Admin (mọi mẫu) (BE-7;
 * layout khu đã chặn Staff). Cùng nội dung với hộp "Quản lý mẫu" trong Hộp thư.
 */
export default function TrangMauTraLoi() {
  return <HopQuanLyMau trang />;
}
