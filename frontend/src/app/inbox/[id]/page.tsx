"use client";

/**
 * Khung chat của một hội thoại — GĐ2 mới xác nhận điều hướng và dòng đang chọn.
 *
 * Đọc tin, ô soạn, các nút Nhận việc/Phân phòng/Đóng là GĐ3–GĐ4; chỗ này cố ý
 * chưa gọi `GET /inbox/{id}` để GĐ2 chỉ chứng minh phần danh sách chạy đúng.
 */

import { useParams } from "next/navigation";

export default function ChiTietHoiThoaiPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="flex flex-1 items-center justify-center bg-surface px-6">
      <div className="max-w-md text-center">
        <p className="text-sm font-medium text-foreground">Đã chọn hội thoại</p>
        <p className="mt-1 break-all font-mono text-xs text-muted">
          {params.id}
        </p>
        <p className="mt-4 text-xs text-muted-soft">
          Khung chat và ô trả lời sẽ có ở giai đoạn 3.
        </p>
      </div>
    </div>
  );
}
