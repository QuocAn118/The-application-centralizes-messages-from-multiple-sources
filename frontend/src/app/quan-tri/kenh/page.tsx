import { ChanTheoVai } from "@/components/chan-theo-vai";
import { ManKenh } from "@/components/quan-tri/man-kenh";

/** `/quan-tri/kenh` — chỉ Admin (`connect_channel.py:43` gọi `bao_dam_admin`). */
export default function TrangKenh() {
  return (
    <ChanTheoVai cho="chiAdmin">
      <ManKenh />
    </ChanTheoVai>
  );
}
