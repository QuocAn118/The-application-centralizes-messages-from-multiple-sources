import { notFound } from "next/navigation";
import { TrangMau } from "./trang-mau";

/**
 * Trang xem toàn bộ design system (redesign Phần 1). **Chỉ môi trường dev**: bản
 * build production trả 404 — trang này hiện component với dữ liệu giả, không
 * có chỗ trên sản phẩm thật.
 *
 * Không bọc `AuthGuard`: người duyệt giao diện không cần đăng nhập để xem.
 */
export default function TrangDesignSystem() {
  if (process.env.NODE_ENV === "production") notFound();
  return <TrangMau />;
}
