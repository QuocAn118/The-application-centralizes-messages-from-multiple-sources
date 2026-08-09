/**
 * Chưa chọn hội thoại nào — hướng dẫn người dùng (spec §4.2 "Rỗng").
 *
 * Khung chat thật nằm ở `/inbox/[id]` (GĐ3).
 */

import { t } from "@/lib/i18n";

export default function InboxPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-surface px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white text-muted-soft">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <path d="M4 4h16v12H7l-3 3V4Z" />
          </svg>
        </div>
        <p className="mt-4 text-sm font-medium text-foreground">
          {t("inbox.chonHoiThoai")}
        </p>
        <p className="mt-1 text-xs text-muted">
          {t("inbox.chonHoiThoaiPhu")}
        </p>
      </div>
    </div>
  );
}
