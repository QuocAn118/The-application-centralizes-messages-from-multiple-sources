import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";
import { TabTuKhoa } from "@/components/tab-tu-khoa";

/**
 * Khung của mọi màn `/tu-khoa/*` (#F4, trả nợ N6).
 *
 * KHÔNG có `ChanTheoVai` — giống khu Nhân sự của #F3, khác khu Cấu hình của
 * #F2. Backend cho **mọi vai** đọc từ khoá và kết quả phân tích trong phạm vi
 * phòng mình (`GET /keywords`, `GET /analyses` trả 200 cho Staff; chỉ CRUD mới
 * 403). Chặn Staff ở cửa là chặn nhầm.
 *
 * Trước đây hai màn này nằm trong `/quan-tri` nên bị cổng của #F2 chặn Staff.
 * Tách hẳn ra đây thay vì nới cổng cũ: cổng đó đang bảo vệ bốn màn quản trị
 * thật sự chỉ dành cho Admin/Manager, đụng vào là rủi ro cho cả bốn.
 */
export default function TuKhoaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <NavRail />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-surface">
          <TabTuKhoa />
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </AuthGuard>
  );
}
