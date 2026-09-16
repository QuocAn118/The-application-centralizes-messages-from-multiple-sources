import { ManNguoiDung } from "@/components/quan-tri/man-nguoi-dung";

/**
 * `/quan-tri/nguoi-dung` — Admin thấy mọi người, Manager chỉ thấy phòng mình
 * (backend ghi đè `department_id`, xem RB-2).
 */
export default function TrangNguoiDung() {
  return <ManNguoiDung />;
}
