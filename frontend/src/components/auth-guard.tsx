"use client";

/**
 * Chặn truy cập khi chưa đăng nhập.
 *
 * Đây chỉ là lớp UX: server mới là trọng tài quyền (RB-3). Không bao giờ dựa
 * vào guard này để giấu dữ liệu — dữ liệu được backend lọc theo vai.
 */

import { useEffect } from "react";
import { t } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <p className="text-sm text-muted">{t("chung.dangTai")}</p>
      </div>
    );
  }

  // Đang chuyển hướng — không nháy nội dung được bảo vệ.
  if (!user) return null;

  return <>{children}</>;
}
