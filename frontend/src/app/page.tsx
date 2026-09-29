"use client";

/**
 * Trang gốc chỉ điều hướng: đã đăng nhập → `/inbox`, chưa thì `/login`.
 */

import { useEffect } from "react";
import { t } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? "/inbox" : "/login");
  }, [user, isLoading, router]);

  return (
    <div className="flex min-h-screen flex-1 items-center justify-center bg-paper">
      <p className="text-sm text-ink-2">{t("chung.dangTai")}</p>
    </div>
  );
}
