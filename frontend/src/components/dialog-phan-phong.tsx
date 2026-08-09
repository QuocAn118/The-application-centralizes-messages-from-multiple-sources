"use client";

/**
 * Hộp thoại phân phòng ban (mockup Stitch "Phân phòng ban - OmniChat").
 *
 * Danh sách phòng đã lọc theo quyền: Manager chỉ được phân về phòng của mình,
 * nên hiện cả danh sách rồi để server trả `ASSIGN_OUT_OF_SCOPE` là mời người
 * dùng vào một thất bại đã biết trước.
 */

import { useEffect, useRef, useState } from "react";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { khoaPhongBan, layPhongBanHoatDong } from "@/lib/inbox-api";
import { phongCoTheChon, type Actor } from "@/lib/quyen-hanh-dong";

export function DialogPhanPhong({
  actor,
  tenKhach,
  dangGui,
  loi,
  onDong,
  onXacNhan,
}: {
  actor: Actor;
  tenKhach: string;
  dangGui: boolean;
  loi: string | null;
  onDong: () => void;
  onXacNhan: (departmentId: string) => void;
}) {
  const [chonTay, setChonTay] = useState<string | null>(null);
  const hopRef = useRef<HTMLDivElement>(null);

  const { data, isPending, isError } = useQuery({
    queryKey: khoaPhongBan,
    queryFn: ({ signal }) => layPhongBanHoatDong(signal),
  });

  const phongBan = data ? phongCoTheChon(actor, data.items) : [];

  // Chỉ có một lựa chọn (Manager) thì coi như đã chọn sẵn — bắt bấm thêm một
  // lần là vô ích. Tính khi render thay vì đồng bộ bằng effect: giá trị này suy
  // ra được từ dữ liệu, không phải trạng thái độc lập.
  const dangChon = chonTay ?? (phongBan.length === 1 ? phongBan[0].id : null);

  // Esc để đóng: hộp thoại nào cũng nên thoát được bằng bàn phím.
  useEffect(() => {
    function xuLy(e: KeyboardEvent) {
      if (e.key === "Escape") onDong();
    }
    document.addEventListener("keydown", xuLy);
    hopRef.current?.focus();
    return () => document.removeEventListener("keydown", xuLy);
  }, [onDong]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={(e) => {
        // Bấm ra nền thì đóng, nhưng bấm bên trong hộp thì không.
        if (e.target === e.currentTarget) onDong();
      }}
    >
      <div
        ref={hopRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tieu-de-phan-phong"
        className="w-full max-w-[440px] rounded-lg bg-white p-6 shadow-xl outline-none"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="tieu-de-phan-phong" className="text-base font-bold text-foreground">
            {t("phanPhong.tieuDe")}
          </h2>
          <button
            type="button"
            onClick={onDong}
            aria-label={t("chung.dong")}
            className="text-muted-soft transition hover:text-muted"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mt-1 text-sm text-muted">
          Chọn phòng ban tiếp nhận hội thoại của {tenKhach}.
        </p>

        <div className="mt-5">
          <p className="mb-2 text-sm font-medium text-foreground">{t("phanPhong.phongBan")}</p>

          {isPending && <p className="text-xs text-muted">{t("phanPhong.dangTai")}</p>}

          {isError && (
            <p className="text-xs text-danger-fg">{t("phanPhong.loiTai")}</p>
          )}

          {!isPending && !isError && phongBan.length === 0 && (
            <p className="text-xs text-muted">
              {t("phanPhong.khongCoPhong")}
            </p>
          )}

          <div className="space-y-2">
            {phongBan.map((phong) => {
              const chon = dangChon === phong.id;
              return (
                <label
                  key={phong.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3.5 py-3 transition ${
                    chon
                      ? "border-primary bg-primary-soft"
                      : "border-border-subtle hover:bg-surface"
                  }`}
                >
                  <input
                    type="radio"
                    name="phong-ban"
                    value={phong.id}
                    checked={chon}
                    onChange={() => setChonTay(phong.id)}
                    className="h-4 w-4 accent-primary"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-foreground">
                      {phong.name}
                    </span>
                    {phong.description && (
                      <span className="block truncate text-xs text-muted">
                        {phong.description}
                      </span>
                    )}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {loi && (
          <p
            role="alert"
            className="mt-4 rounded-lg border border-danger-border bg-danger-bg px-3.5 py-2 text-xs text-danger-fg"
          >
            {loi}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onDong}
            className="rounded-lg border border-border-subtle px-4 py-2 text-sm font-medium text-muted transition hover:bg-surface"
          >
            {t("chung.huy")}
          </button>
          <button
            type="button"
            disabled={!dangChon || dangGui}
            onClick={() => dangChon && onXacNhan(dangChon)}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {dangGui ? t("hanhDong.dangPhan") : t("hanhDong.phanPhong")}
          </button>
        </div>
      </div>
    </div>
  );
}
