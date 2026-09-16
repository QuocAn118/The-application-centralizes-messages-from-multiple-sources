import { ChanTheoVai } from "@/components/chan-theo-vai";
import { ManNhatKy } from "@/components/quan-tri/man-nhat-ky";

/** `/quan-tri/nhat-ky` — chỉ Admin (`department_router.py:134`). */
export default function TrangNhatKy() {
  return (
    <ChanTheoVai cho="chiAdmin">
      <ManNhatKy />
    </ChanTheoVai>
  );
}
