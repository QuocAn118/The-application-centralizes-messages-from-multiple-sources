import { ChanTheoVai } from "@/components/chan-theo-vai";
import { ManKenh } from "@/components/quan-tri/man-kenh";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Kênh" };

/** `/quan-tri/kenh` — chỉ Admin (`connect_channel.py:43` gọi `bao_dam_admin`). */
export default function TrangKenh() {
  return (
    <ChanTheoVai cho="chiAdmin">
      <ManKenh />
    </ChanTheoVai>
  );
}
