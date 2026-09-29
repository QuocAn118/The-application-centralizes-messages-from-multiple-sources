import { ManNguoiDung } from "@/components/quan-tri/man-nguoi-dung";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Người dùng" };

/**
 * `/quan-tri/nguoi-dung` — Admin thấy mọi người, Manager chỉ thấy phòng mình
 * (backend ghi đè `department_id`, xem RB-2).
 */
export default function TrangNguoiDung() {
  return <ManNguoiDung />;
}
