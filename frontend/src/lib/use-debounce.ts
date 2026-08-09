"use client";

/** Trả về `giaTri` sau khi nó ngừng đổi trong `tre` mili-giây. */

import { useEffect, useState } from "react";

export function useDebounce<T>(giaTri: T, tre = 300): T {
  const [daHoan, setDaHoan] = useState(giaTri);

  useEffect(() => {
    const hen = setTimeout(() => setDaHoan(giaTri), tre);
    // Dọn hẹn cũ mỗi lần giá trị đổi: không dọn thì mọi nhịp gõ đều nổ sau
    // đúng `tre` ms và debounce mất tác dụng.
    return () => clearTimeout(hen);
  }, [giaTri, tre]);

  return daHoan;
}
