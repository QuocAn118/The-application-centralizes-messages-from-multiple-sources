"use client";

/**
 * Khung màn hộp thư — GĐ1 mới dựng vỏ và xác nhận phiên đăng nhập chạy đúng.
 *
 * Danh sách hội thoại (cột trái) là GĐ2, khung chat là GĐ3. Chỗ này cố ý chưa
 * gọi `GET /inbox` để GĐ1 chỉ chứng minh đúng một việc: auth hoạt động.
 */

import { useAuth } from "@/lib/auth-context";

export default function InboxPage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-1 items-center justify-center bg-surface">
      <div className="max-w-md rounded-lg border border-border-subtle bg-white p-8 text-center">
        <h1 className="text-lg font-semibold">Hộp thư</h1>
        <p className="mt-2 text-sm text-muted">
          Đã đăng nhập:{" "}
          <span className="font-medium text-foreground">{user?.full_name}</span>{" "}
          ({user?.role})
        </p>
        <p className="mt-4 text-sm text-muted-soft">
          Danh sách hội thoại và khung chat sẽ có ở giai đoạn 2–3.
        </p>
      </div>
    </div>
  );
}
