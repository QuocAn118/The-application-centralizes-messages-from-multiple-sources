import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";
import { ChanTheoVai } from "@/components/chan-theo-vai";
import { TabQuanTri } from "@/components/tab-quan-tri";

/**
 * Khung của mọi màn `/quan-tri/*` (#F2 task 1.2).
 *
 * Khác layout inbox ở chỗ KHÔNG có danh sách hội thoại và KHÔNG mở kết nối
 * realtime: khu quản trị không nhận tín hiệu inbox, mở socket ở đây chỉ tốn
 * kết nối.
 *
 * `ChanTheoVai` nằm trong `AuthGuard` nên chỉ xét vai khi đã biết chắc người
 * dùng là ai — tránh nháy màn "không có quyền" trong lúc còn đang tải phiên.
 */
export default function QuanTriLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <NavRail />
        <ChanTheoVai cho="khuQuanTri">
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-surface">
            <TabQuanTri />
            <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
          </div>
        </ChanTheoVai>
      </div>
    </AuthGuard>
  );
}
