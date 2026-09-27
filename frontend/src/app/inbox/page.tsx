/** Chưa chọn hội thoại nào — khung chat thật ở `/inbox/[id]`. */

import { MessagesSquare } from "lucide-react";
import { t } from "@/lib/i18n";
import { TrangThaiRong } from "@/components/ui/trang-thai";

export default function InboxPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-paper">
      <TrangThaiRong
        icon={MessagesSquare}
        tieuDe={t("inbox.chonHoiThoai")}
        moTa={t("inbox.chonHoiThoaiPhu")}
      />
    </div>
  );
}
