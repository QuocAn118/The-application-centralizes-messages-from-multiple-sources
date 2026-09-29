import { ManNhanVien } from "@/components/bao-cao/man-nhan-vien";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Nhân viên" };

export default function TrangBaoCaoNhanVien() {
  return <ManNhanVien />;
}
