import { ManCaLamViec } from "@/components/nhan-su/man-ca-lam-viec";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Ca làm việc" };

/** `/nhan-su/ca-lam-viec` — mọi vai; Staff chỉ xem ca của chính mình. */
export default function TrangCaLamViec() {
  return <ManCaLamViec />;
}
