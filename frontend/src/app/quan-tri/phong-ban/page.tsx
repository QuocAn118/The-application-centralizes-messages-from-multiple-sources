import { ChanTheoVai } from "@/components/chan-theo-vai";
import { ManPhongBan } from "@/components/quan-tri/man-phong-ban";

/**
 * `/quan-tri/phong-ban` — chỉ Admin.
 *
 * Layout đã chặn ở mức khu (Admin + Manager), nên chặn thêm ở đây: Manager vào
 * được khu nhưng không vào được màn này (`create_department.py:40`).
 */
export default function TrangPhongBan() {
  return (
    <ChanTheoVai cho="chiAdmin">
      <ManPhongBan />
    </ChanTheoVai>
  );
}
