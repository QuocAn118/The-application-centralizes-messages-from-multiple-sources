import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";
import { TabNhanSu } from "@/components/tab-nhan-su";

/**
 * Khung của mọi màn `/nhan-su/*` (#F3 task 1.2).
 *
 * KHÔNG có `ChanTheoVai`: khác khu quản trị, đây là khu mọi vai đều vào được —
 * Staff xem ca của mình, gửi đơn, xem KPI của mình. Backend lọc phạm vi dữ
 * liệu, FE không chặn ở cửa.
 */
export default function NhanSuLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <NavRail />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-surface">
          <TabNhanSu />
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </AuthGuard>
  );
}
