import { ManDonTu } from "@/components/nhan-su/man-don-tu";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Đơn từ" };

/** `/nhan-su/don-tu` — mọi vai vào được, backend lọc phạm vi dữ liệu. */
export default function TrangDonTu() {
  return <ManDonTu />;
}
