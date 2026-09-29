import type { Metadata } from "next";

// page.tsx là client component (không khai `metadata` được) → đặt tiêu đề tab ở đây.
export const metadata: Metadata = { title: "Đổi mật khẩu" };

export default function DoiMatKhauLayout({ children }: { children: React.ReactNode }) {
  return children;
}
