import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";
import { ChanTheoVai } from "@/components/chan-theo-vai";
import { TabBaoCao } from "@/components/tab-bao-cao";

/**
 * Khung của mọi màn `/bao-cao/*` (#F5).
 *
 * Khác `/nhan-su` và `/tu-khoa` (mọi vai): báo cáo tổng hợp **chỉ Manager/Admin**
 * — Staff nhận 403 `ANALYTICS_MANAGER_REQUIRED` ở cả 4 endpoint (đã đo). Vì thế
 * bọc `ChanTheoVai cho="khuQuanTri"` (cùng phạm vi Manager+Admin) như `/quan-tri`,
 * để Staff thấy câu giải thích thay vì một bảng lỗi 403.
 *
 * `ChanTheoVai` nằm trong `AuthGuard` nên chỉ xét vai khi đã biết người dùng —
 * tránh nháy màn "không có quyền" lúc còn tải phiên.
 */
export default function BaoCaoLayout({
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
            <TabBaoCao />
            <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
          </div>
        </ChanTheoVai>
      </div>
    </AuthGuard>
  );
}
