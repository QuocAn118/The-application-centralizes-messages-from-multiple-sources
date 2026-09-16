"use client";

/**
 * Chặn nội dung theo vai trò (#F2 RB-1).
 *
 * **Chỉ là UX, không phải bảo vệ.** Backend đã chặn bằng 403; lớp này chỉ để
 * người không có quyền thấy một câu giải thích thay vì một bảng trống rỗng kèm
 * lỗi đỏ. Không bao giờ dựa vào đây để giấu dữ liệu.
 *
 * Cố ý KHÔNG chuyển hướng: đá người ta về `/inbox` mà không nói gì thì họ
 * tưởng bấm nhầm và sẽ bấm lại. Hiện thẳng lý do rồi cho lối quay về.
 */

import Link from "next/link";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { chiAdmin, vaoDuocKhuQuanTri } from "@/lib/quyen-quan-tri";

/** Phạm vi cần kiểm: cả khu (Admin + Manager) hay riêng màn chỉ-Admin. */
export type PhamVi = "khuQuanTri" | "chiAdmin";

export function ChanTheoVai({
  cho,
  children,
}: {
  cho: PhamVi;
  children: React.ReactNode;
}) {
  const { user } = useAuth();

  // `AuthGuard` bọc ngoài đã bảo đảm có `user`; nhánh này chỉ để type an toàn.
  if (!user) return null;

  const duocVao =
    cho === "chiAdmin" ? chiAdmin(user.role) : vaoDuocKhuQuanTri(user.role);

  if (!duocVao) {
    // `min-h-[60vh]` chứ không chỉ `flex-1`: component này dùng ở HAI chỗ —
    // trực tiếp trong layout (cha là flex ngang, `flex-1` ăn) và lồng trong
    // page (cha là khối cuộn thường, `flex-1` vô tác dụng và nội dung sẽ dính
    // sát mép trên). Chiều cao tối thiểu giữ cho cả hai trường hợp cùng căn giữa.
    return (
      <div className="flex min-h-[60vh] min-w-0 flex-1 flex-col items-center justify-center gap-3 bg-surface px-6 text-center">
        <p className="text-sm text-muted">{t("quanTri.khongCoQuyen")}</p>
        <Link
          href="/inbox"
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          {t("quanTri.veHopThu")}
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
