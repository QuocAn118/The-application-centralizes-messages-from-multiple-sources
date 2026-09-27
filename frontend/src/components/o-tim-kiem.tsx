"use client";

/**
 * Ô tìm kiếm có hoãn nhịp (#F2 task 1.3).
 *
 * Giữ chữ đang gõ ở state nội bộ và chỉ báo ra ngoài sau khi người dùng ngừng
 * gõ — nếu báo ngay thì mỗi phím là một lượt gọi API. Dùng `useDebounce` sẵn
 * có của #F1 thay vì tự hẹn giờ.
 */

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { useDebounce } from "@/lib/use-debounce";
import { ONhap } from "./ui/o-nhap";

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
    <div className="relative w-64">
      <Search
        aria-hidden
        strokeWidth={2.25}
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-2"
      />
      <ONhap
        type="search"
        value={chu}
        onChange={(e) => setChu(e.target.value)}
        placeholder={nhanGoiY}
        aria-label={nhanGoiY}
        className="pl-9"
      />
    </div>
  );
}
