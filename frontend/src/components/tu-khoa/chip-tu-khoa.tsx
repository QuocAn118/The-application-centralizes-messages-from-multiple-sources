"use client";

/**
 * Chip từ khoá + ô thêm nhanh cuối dãy (redesign Phần 4 T1–T3).
 *
 * **T2: "dạng khớp" chỉ ở tooltip** (và trong hộp sửa), không hiện thường trực.
 * Ô thêm nhanh báo trùng bằng **thông điệp server** kèm câu giải thích chuẩn
 * hoá — vẫn giữ RB-3: FE KHÔNG tự bỏ dấu để đoán trùng. Server không trả dạng
 * chuẩn hoá trong lỗi 409, nên chưa chỉ được đúng chip nào bị trùng.
 */

import { useId, useState } from "react";
import { X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { ApiError } from "@/lib/api-client";
import { khoaTuKhoa, taoTuKhoa } from "@/lib/tu-khoa-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ONhap } from "@/components/ui/o-nhap";
import type { Keyword } from "@/lib/types";

export function ChipTuKhoa({
  tuKhoa,
  onSua,
  onXoa,
}: {
  tuKhoa: Keyword;
  /** `null` = chỉ xem (Staff, hoặc Manager nhìn phòng khác). */
  onSua: (() => void) | null;
  onXoa: (() => void) | null;
}) {
  const dangKhop = t("tuKhoa.dangKhop", { chuan: tuKhoa.normalized });
  return (
    <li
      title={dangKhop}
      className="inline-flex items-stretch overflow-hidden rounded-nb border-2 border-ink bg-card text-sm font-semibold text-ink"
    >
      {onSua ? (
        <button
          type="button"
          onClick={onSua}
          aria-label={`${t("tuKhoa.sua")} ${tuKhoa.text}`}
          className="px-2.5 py-1 hover:bg-accent focus-visible:bg-accent"
        >
          {tuKhoa.text}
        </button>
      ) : (
        <span className="px-2.5 py-1">{tuKhoa.text}</span>
      )}
      {onXoa && (
        <button
          type="button"
          onClick={onXoa}
          aria-label={`${t("tuKhoa.xoa")} ${tuKhoa.text}`}
          title={t("tuKhoa.xoa")}
          className="inline-flex items-center border-l-2 border-ink px-1.5 hover:bg-bad hover:text-card focus-visible:bg-bad focus-visible:text-card"
        >
          <X aria-hidden className="size-3.5" strokeWidth={2.75} />
        </button>
      )}
    </li>
  );
}

/** Gõ + Enter để thêm vào đúng phòng này. Giữ focus sau khi thêm để gõ tiếp. */
export function OThemNhanh({ phongId, tenPhong }: { phongId: string; tenPhong: string }) {
  const queryClient = useQueryClient();
  const idLoi = useId();
  const [text, setText] = useState("");

  const them = useMutation({
    mutationFn: (tu: string) => taoTuKhoa({ department_id: phongId, text: tu }),
    onSuccess: () => {
      setText("");
      void queryClient.invalidateQueries({ queryKey: khoaTuKhoa.tuKhoa.all });
    },
  });
  const trung = them.error instanceof ApiError && them.error.code === "KEYWORD_DUPLICATE";

  return (
    <li className="flex max-w-80 flex-col gap-1">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const tu = text.trim();
          if (tu && !them.isPending) them.mutate(tu);
        }}
      >
        <ONhap
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (them.isError) them.reset();
          }}
          // readOnly thay vì disabled: disabled làm rơi focus, người dùng phải bấm lại mới gõ tiếp.
          readOnly={them.isPending}
          maxLength={200}
          placeholder={t("tuKhoa.themNhanhGoiY")}
          aria-label={t("tuKhoa.themNhanhNhan", { phong: tenPhong })}
          aria-describedby={them.isError ? idLoi : undefined}
          coLoi={them.isError}
          className="!h-8 w-56"
        />
      </form>
      {them.isError && (
        <p id={idLoi} role="alert" className="text-xs font-semibold text-bad">
          {thongDiepLoi(them.error)}
          {trung && <span className="block font-normal text-ink-2">{t("tuKhoa.giaiThichChuanHoa")}</span>}
        </p>
      )}
    </li>
  );
}
