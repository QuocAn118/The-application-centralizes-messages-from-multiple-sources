import { ManTuKhoa } from "@/components/tu-khoa/man-tu-khoa";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Từ khoá" };

/** `/tu-khoa/danh-sach` — mọi vai; Staff xem, Manager/Admin sửa phòng mình. */
export default function TrangTuKhoa() {
  return <ManTuKhoa />;
}
