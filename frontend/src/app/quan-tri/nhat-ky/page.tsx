import { ChanTheoVai } from "@/components/chan-theo-vai";
import { ManNhatKy } from "@/components/quan-tri/man-nhat-ky";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Nhật ký" };

/** `/quan-tri/nhat-ky` — chỉ Admin (`department_router.py:134`). */
export default function TrangNhatKy() {
  return (
    <ChanTheoVai cho="chiAdmin">
      <ManNhatKy />
    </ChanTheoVai>
  );
}
