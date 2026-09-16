"use client";

/**
 * Ô tìm kiếm có hoãn nhịp (#F2 task 1.3).
 *
 * Giữ chữ đang gõ ở state nội bộ và chỉ báo ra ngoài sau khi người dùng ngừng
 * gõ — nếu báo ngay thì mỗi phím là một lượt gọi API. Dùng `useDebounce` sẵn
 * có của #F1 thay vì tự hẹn giờ.
 */

import { useEffect, useState } from "react";
import { useDebounce } from "@/lib/use-debounce";

export function OTimKiem({
  giaTriDau = "",
  nhanGoiY,
  doiTuKhoa,
}: {
  giaTriDau?: string;
  nhanGoiY: string;
  doiTuKhoa: (tuKhoa: string) => void;
}) {
  const [chu, setChu] = useState(giaTriDau);
  const daHoan = useDebounce(chu, 300);

  useEffect(() => {
    doiTuKhoa(daHoan.trim());
    // `doiTuKhoa` cố tình không nằm trong deps: nơi gọi hay truyền hàm inline,
    // đưa vào sẽ bắn lại mỗi lần render cha.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daHoan]);

  return (
    <input
      type="search"
      value={chu}
      onChange={(e) => setChu(e.target.value)}
      placeholder={nhanGoiY}
      aria-label={nhanGoiY}
      className="w-64 rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted-soft focus:border-primary"
    />
  );
}
