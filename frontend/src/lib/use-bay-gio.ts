"use client";

import { useEffect, useState } from "react";

/** "Bây giờ" cập nhật mỗi `nhipMs` — cho mốc tương đối / "Chờ N phút" tự nhảy mà không gọi API. */
export function useBayGio(nhipMs = 60_000): Date {
  const [bayGio, setBayGio] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setBayGio(new Date()), nhipMs);
    return () => clearInterval(id);
  }, [nhipMs]);
  return bayGio;
}
