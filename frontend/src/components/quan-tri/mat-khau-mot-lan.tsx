"use client";

/**
 * Khối "mật khẩu tạm — chỉ hiện MỘT LẦN" (RB-3), dùng chung cho Tạo tài khoản và
 * Đặt lại mật khẩu. Mật khẩu chỉ sống trong state của hộp thoại gọi nó: không
 * `localStorage`, không URL, không log.
 */

import { useState } from "react";
import { Check, Copy, TriangleAlert } from "lucide-react";
import { t } from "@/lib/i18n";
import { Nut } from "@/components/ui/nut";

export function MatKhauMotLan({ matKhau, ghiChu }: { matKhau: string; ghiChu: string }) {
  const [daSaoChep, setDaSaoChep] = useState(false);

  return (
    <div className="mt-4 flex flex-col gap-3">
      <p className="flex items-start gap-2 rounded-nb border-2 border-wait bg-wait-bg px-3 py-2.5 text-sm font-semibold text-wait">
        <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" strokeWidth={2.5} />
        {t("nguoiDung.canhBaoMotLan")}
      </p>
      <div>
        <p className="text-sm font-semibold text-ink">{t("nguoiDung.matKhauTam")}</p>
        <div className="mt-1.5 flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-nb border-2 border-ink bg-sunken px-3 py-2 font-mono text-base font-bold text-ink">
            {matKhau}
          </code>
          <Nut
            icon={daSaoChep ? Check : Copy}
            onClick={() => {
              void navigator.clipboard
                .writeText(matKhau)
                .then(() => setDaSaoChep(true))
                // Trình duyệt có thể chặn clipboard (không phải HTTPS, không có
                // tương tác…). Nuốt lỗi: mật khẩu vẫn đang hiện, chép tay được.
                .catch(() => setDaSaoChep(false));
            }}
          >
            {daSaoChep ? t("nguoiDung.daSaoChep") : t("nguoiDung.saoChep")}
          </Nut>
        </div>
      </div>
      <p className="text-sm text-ink-2">{ghiChu}</p>
    </div>
  );
}
