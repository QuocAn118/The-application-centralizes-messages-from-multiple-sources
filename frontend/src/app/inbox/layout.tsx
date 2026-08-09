import { Suspense } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";
import { DanhSachInbox } from "@/components/danh-sach-inbox";
import { CauNoiRealtime } from "@/components/cau-noi-realtime";

/**
 * Khung của mọi màn `/inbox*`: nav trái + danh sách + vùng nội dung (spec §4.2).
 *
 * Danh sách nằm ở layout nên khi chuyển giữa các hội thoại nó KHÔNG bị dựng
 * lại — vị trí cuộn và cache được giữ nguyên.
 */
export default function InboxLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      {/* Nằm trong AuthGuard nên chỉ chạy khi đã đăng nhập; đặt ở layout để
          kết nối sống suốt phiên, không đứt khi chuyển hội thoại. */}
      <CauNoiRealtime />
      <div className="flex h-screen overflow-hidden">
        <NavRail />
        {/* `useSearchParams` cần Suspense bao ngoài khi build tĩnh. */}
        <Suspense fallback={<div className="w-[360px] border-r border-border-subtle bg-white" />}>
          <DanhSachInbox />
        </Suspense>
        <div className="flex min-w-0 flex-1">{children}</div>
      </div>
    </AuthGuard>
  );
}
