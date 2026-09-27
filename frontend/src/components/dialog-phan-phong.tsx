"use client";

/**
 * Hộp thoại phân phòng ban (redesign 2a: dựng trên `HopThoai` — Radix lo focus,
 * Esc, bấm nền).
 *
 * Danh sách phòng đã lọc theo quyền: Manager chỉ được phân về phòng của mình,
 * nên hiện cả danh sách rồi để server trả `ASSIGN_OUT_OF_SCOPE` là mời người
 * dùng vào một thất bại đã biết trước.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaPhongBan, layPhongBanHoatDong } from "@/lib/inbox-api";
import { phongCoTheChon, type Actor } from "@/lib/quyen-hanh-dong";
import { HopThoai, NutChinh, NutPhu } from "./hop-thoai";

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

  const { data, isPending, isError } = useQuery({
    queryKey: khoaPhongBan,
    queryFn: ({ signal }) => layPhongBanHoatDong(signal),
  });

  const phongBan = data ? phongCoTheChon(actor, data.items) : [];
  // Chỉ một lựa chọn (Manager) thì coi như đã chọn sẵn — suy từ dữ liệu, không phải state.
  const dangChon = chonTay ?? (phongBan.length === 1 ? phongBan[0].id : null);

  return (
    <HopThoai
      tieuDe={t("phanPhong.tieuDe")}
      moTa={`Chọn phòng ban tiếp nhận hội thoại của ${tenKhach}.`}
      loi={loi}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong}>{t("chung.huy")}</NutPhu>
          <NutChinh disabled={!dangChon || dangGui} onClick={() => dangChon && onXacNhan(dangChon)}>
            {dangGui ? t("hanhDong.dangPhan") : t("hanhDong.phanPhong")}
          </NutChinh>
        </>
      }
    >
      {isPending && <p className="text-sm text-ink-2">{t("phanPhong.dangTai")}</p>}
      {isError && <p className="text-sm font-semibold text-bad">{t("phanPhong.loiTai")}</p>}
      {!isPending && !isError && phongBan.length === 0 && (
        <p className="text-sm text-ink-2">{t("phanPhong.khongCoPhong")}</p>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-bold text-ink">{t("phanPhong.phongBan")}</legend>
        {phongBan.map((phong) => {
          const chon = dangChon === phong.id;
          return (
            <label
              key={phong.id}
              className={`flex cursor-pointer items-center gap-3 rounded-nb border-2 border-ink px-3.5 py-3 ${
                chon ? "bg-accent" : "bg-card hover:bg-sunken"
              }`}
            >
              <input
                type="radio"
                name="phong-ban"
                value={phong.id}
                checked={chon}
                onChange={() => setChonTay(phong.id)}
                className="size-4 accent-ink"
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold text-ink">{phong.name}</span>
                {phong.description && (
                  <span className="block truncate text-xs text-ink-2">{phong.description}</span>
                )}
              </span>
            </label>
          );
        })}
      </fieldset>
    </HopThoai>
  );
}
