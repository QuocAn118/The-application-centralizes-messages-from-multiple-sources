"use client";

/**
 * Thanh tab khu Cấu hình: Người dùng · Phòng ban · Kênh · Nhật ký.
 *
 * Manager chỉ thấy tab "Người dùng" — ba màn còn lại chỉ Admin (spec #F2 §2).
 * Ẩn hẳn tab thay vì hiện rồi chặn khi bấm: thấy tab mà vào không được thì trông
 * như hỏng. (Route vẫn là `/quan-tri/*`; chỉ chữ hiển thị đổi thành "Cấu hình".)
 */

import { t, type KhoaChuoi } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { chiAdmin } from "@/lib/quyen-quan-tri";
import { TabKhu } from "./ui/tab-khu";

const TAB: { duongDan: string; nhan: KhoaChuoi; riengAdmin: boolean }[] = [
  { duongDan: "/quan-tri/nguoi-dung", nhan: "quanTri.tabNguoiDung", riengAdmin: false },
  { duongDan: "/quan-tri/phong-ban", nhan: "quanTri.tabPhongBan", riengAdmin: true },
  { duongDan: "/quan-tri/kenh", nhan: "quanTri.tabKenh", riengAdmin: true },
  { duongDan: "/quan-tri/nhat-ky", nhan: "quanTri.tabNhatKy", riengAdmin: true },
];

export function TabQuanTri() {
  const { user } = useAuth();
  if (!user) return null;

  const laAdmin = chiAdmin(user.role);
  return (
    <TabKhu
      tieuDe={t("quanTri.tieuDe")}
      tab={TAB.filter((muc) => laAdmin || !muc.riengAdmin).map((muc) => ({
        duongDan: muc.duongDan,
        nhan: t(muc.nhan),
      }))}
    />
  );
}
