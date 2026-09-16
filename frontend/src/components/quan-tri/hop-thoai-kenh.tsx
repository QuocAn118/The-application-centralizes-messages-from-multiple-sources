"use client";

/**
 * Kết nối / sửa kênh (#F2 task 3.2–3.4).
 *
 * Đây là màn nhạy cảm nhất của #F2 vì nó chạm token thật. Ba quy tắc, mỗi cái
 * đều đọc từ schema backend chứ không suy đoán:
 *
 * **RB-6 — credential chỉ ghi vào, không đọc ra.** `ChannelResponse` không trả
 * credential, nên khi sửa thì ô token để TRỐNG, không phải điền sẵn dấu sao.
 * Điền dấu sao sẽ khiến người dùng tưởng đó là token thật và bấm sao chép.
 *
 * **RB-6 (tiếp) — token không lọt vào thông báo lỗi.** `thongDiepLoi` chỉ đọc
 * `message` của server, mà server không bao giờ trả credential; nhưng vẫn phải
 * cẩn thận không tự nối giá trị ô nhập vào bất kỳ chuỗi hiển thị nào.
 *
 * **RB-7 — gỡ phòng phải dùng `clear_department: true`.** Gửi
 * `department_id: null` bị `UpdateChannelRequest` hiểu là "không đổi", nên gỡ
 * sẽ im lặng không có tác dụng — đúng loại lỗi trông như đã làm xong.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_KENH } from "@/lib/hien-thi";
import { ketNoiKenh, khoaQuanTri, suaKenh, thanSuaKenh } from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type { Channel, Department, Platform } from "@/lib/types";

const LOP_O_NHAP =
  "mt-1 w-full rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted-soft focus:border-primary";

const NEN_TANG: readonly Platform[] = [
  "ZALO",
  "FACEBOOK",
  "INSTAGRAM",
  "TELEGRAM",
] as const;

export function HopThoaiKenh({
  kenh,
  phongBan,
  onDong,
}: {
  /** `null` = kết nối kênh mới. */
  kenh: Channel | null;
  phongBan: Department[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const dangSua = kenh !== null;

  const [ten, setTen] = useState(kenh?.name ?? "");
  const [nenTang, setNenTang] = useState<Platform>(kenh?.platform ?? "ZALO");
  const [maKenh, setMaKenh] = useState(kenh?.external_channel_id ?? "");
  const [phongId, setPhongId] = useState(kenh?.department_id ?? "");
  // Luôn bắt đầu RỖNG, kể cả khi sửa: không có token nào để điền sẵn.
  const [token, setToken] = useState("");

  const phongHoatDong = phongBan.filter((p) => p.is_active);

  const hopLe = dangSua
    ? ten.trim().length > 0
    : ten.trim().length > 0 && maKenh.trim().length > 0 && token.length > 0;

  const luu = useMutation({
    mutationFn: () => {
      if (kenh) {
        // `thanSuaKenh` giữ hai quy tắc dễ sai (RB-6 token trống = giữ nguyên,
        // RB-7 gỡ phòng bằng `clear_department`) ở một chỗ có test bao.
        return suaKenh(kenh.id, thanSuaKenh({ ten, token, phongId }));
      }
      return ketNoiKenh({
        platform: nenTang,
        external_channel_id: maKenh.trim(),
        name: ten.trim(),
        credential: token,
        department_id: phongId || null,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaQuanTri.kenh.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={dangSua ? t("kenh.suaTieuDe") : t("kenh.ketNoi")}
      moTa={dangSua ? kenh.name : undefined}
      loi={luu.isError ? thongDiepLoi(luu.error) : null}
      onDong={onDong}
      chanDuoi={
        <>
          <NutPhu onClick={onDong} disabled={luu.isPending}>
            {t("chung.huy")}
          </NutPhu>
          <NutChinh onClick={() => luu.mutate()} disabled={!hopLe || luu.isPending}>
            {luu.isPending ? t("nguoiDung.dangLuu") : t("nguoiDung.luu")}
          </NutChinh>
        </>
      }
    >
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className="text-xs font-medium text-muted">{t("kenh.ten")}</span>
          <input
            value={ten}
            onChange={(e) => setTen(e.target.value)}
            maxLength={200}
            className={LOP_O_NHAP}
          />
        </label>

        {/* Nền tảng và mã kênh KHÔNG sửa được: `UpdateChannelRequest` không
            nhận chúng. Khi sửa thì hiện dạng chỉ-đọc thay vì ô nhập, để không
            mời người dùng gõ vào thứ sẽ bị bỏ qua. */}
        {dangSua ? (
          <div className="flex gap-3">
            <div className="flex-1">
              <span className="text-xs font-medium text-muted">{t("kenh.nenTang")}</span>
              <p className="mt-1 text-sm text-foreground">{NHAN_KENH[kenh.platform]}</p>
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-medium text-muted">{t("kenh.maKenh")}</span>
              <p className="mt-1 truncate font-mono text-sm text-foreground">
                {kenh.external_channel_id}
              </p>
            </div>
          </div>
        ) : (
          <>
            <label className="block">
              <span className="text-xs font-medium text-muted">{t("kenh.nenTang")}</span>
              <select
                value={nenTang}
                onChange={(e) => setNenTang(e.target.value as Platform)}
                className={LOP_O_NHAP}
              >
                {NEN_TANG.map((p) => (
                  <option key={p} value={p}>
                    {NHAN_KENH[p]}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-medium text-muted">{t("kenh.maKenh")}</span>
              <input
                value={maKenh}
                onChange={(e) => setMaKenh(e.target.value)}
                placeholder={t("kenh.maKenhGoiY")}
                maxLength={255}
                className={`${LOP_O_NHAP} font-mono`}
              />
            </label>
          </>
        )}

        <label className="block">
          <span className="text-xs font-medium text-muted">
            {t("kenh.phongPhuTrach")}
          </span>
          <select
            value={phongId}
            onChange={(e) => setPhongId(e.target.value)}
            className={LOP_O_NHAP}
          >
            <option value="">{t("kenh.khongPhong")}</option>
            {phongHoatDong.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-muted">{t("kenh.token")}</span>
          <input
            // LUÔN `type="password"`, KHÔNG có nút hiện/ẩn (RB-6). Khác ô mật
            // khẩu tạm lúc tạo tài khoản — ở đó Admin phải đọc để gửi cho
            // người dùng, còn token nền tảng thì dán vào là xong, không ai cần
            // nhìn lại. Bớt một đường lộ token trên màn hình.
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={dangSua ? t("kenh.tokenGiuNguyen") : t("kenh.tokenGoiY")}
            className={LOP_O_NHAP}
          />
          <span className="mt-1 block text-xs text-muted-soft">
            {dangSua ? t("kenh.tokenKhongDocLai") : t("kenh.tokenGoiY")}
          </span>
        </label>
      </div>
    </HopThoai>
  );
}
