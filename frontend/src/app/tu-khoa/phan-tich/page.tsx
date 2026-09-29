import { ManPhanTich } from "@/components/tu-khoa/man-phan-tich";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Phân tích AI" };

/** `/tu-khoa/phan-tich` — mọi vai; chỉ đọc, phạm vi theo phòng. */
export default function TrangPhanTich() {
  return <ManPhanTich />;
}
