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
import { loiTheoTruong } from "@/lib/loi-truong";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import { IconKenh } from "@/components/ui/icon-kenh";
import type { Channel, Department, Platform } from "@/lib/types";

type O = "ten" | "maKenh" | "token";
const THEO_MA: Partial<Record<string, O>> = {
  CHANNEL_ALREADY_CONNECTED: "maKenh",
  EMPTY_EXTERNAL_CHANNEL_ID: "maKenh",
};
const THEO_TEN: Partial<Record<string, O>> = { name: "ten", external_channel_id: "maKenh", credential: "token" };

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

  // Lỗi server về đúng ô (§4.6). `loiTheoTruong` chỉ đọc `message` của server —
  // không bao giờ nối giá trị ô token vào chuỗi hiển thị (RB-6).
  const loi = luu.isError ? loiTheoTruong(luu.error, THEO_MA, THEO_TEN) : null;
  const loiO = (o: O) => (loi?.truong === o ? loi.thongDiep : null);

  return (
    <HopThoai
      tieuDe={dangSua ? t("kenh.suaTieuDe") : t("kenh.ketNoi")}
      moTa={dangSua ? kenh.name : undefined}
      loi={loi && !loi.truong ? loi.thongDiep : null}
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
      <div className="mt-4 flex flex-col gap-4">
        <Truong nhan={t("kenh.ten")} batBuoc loi={loiO("ten")}>
          {(o) => <ONhap {...o} value={ten} onChange={(e) => setTen(e.target.value)} maxLength={200} />}
        </Truong>

        {/* Nền tảng và mã kênh KHÔNG sửa được: `UpdateChannelRequest` không
            nhận chúng. Khi sửa thì hiện dạng chỉ-đọc thay vì ô nhập, để không
            mời người dùng gõ vào thứ sẽ bị bỏ qua. */}
        {dangSua ? (
          <dl className="grid grid-cols-2 gap-3 rounded-nb border-2 border-line bg-sunken px-3 py-2.5">
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-ink-2">{t("kenh.nenTang")}</dt>
              <dd className="mt-1 inline-flex items-center gap-2 text-sm font-semibold text-ink">
                <span aria-hidden className="inline-flex">
                  <IconKenh kenh={kenh.platform} />
                </span>
                {NHAN_KENH[kenh.platform]}
              </dd>
            </div>
            <div className="min-w-0">
              <dt className="text-xs font-bold uppercase tracking-wide text-ink-2">{t("kenh.maKenh")}</dt>
              <dd className="mt-1 truncate font-mono text-sm text-ink">{kenh.external_channel_id}</dd>
            </div>
          </dl>
        ) : (
          <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3">
            <Truong nhan={t("kenh.nenTang")}>
              {(o) => (
                <OChon {...o} value={nenTang} onChange={(e) => setNenTang(e.target.value as Platform)}>
                  {NEN_TANG.map((p) => (
                    <option key={p} value={p}>
                      {NHAN_KENH[p]}
                    </option>
                  ))}
                </OChon>
              )}
            </Truong>
            <Truong nhan={t("kenh.maKenh")} batBuoc loi={loiO("maKenh")}>
              {(o) => (
                <ONhap
                  {...o}
                  value={maKenh}
                  onChange={(e) => setMaKenh(e.target.value)}
                  placeholder={t("kenh.maKenhGoiY")}
                  maxLength={255}
                  className="font-mono"
                />
              )}
            </Truong>
          </div>
        )}

        <Truong nhan={t("kenh.phongPhuTrach")}>
          {(o) => (
            <OChon {...o} value={phongId} onChange={(e) => setPhongId(e.target.value)}>
              <option value="">{t("kenh.khongPhong")}</option>
              {phongHoatDong.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </OChon>
          )}
        </Truong>

        <Truong
          nhan={t("kenh.token")}
          batBuoc={!dangSua}
          goiY={dangSua ? t("kenh.tokenKhongDocLai") : t("kenh.tokenGoiY")}
          loi={loiO("token")}
        >
          {(o) => (
            <ONhap
              {...o}
              // LUÔN `type="password"`, KHÔNG có nút hiện/ẩn (RB-6). Khác ô mật
              // khẩu tạm lúc tạo tài khoản — ở đó Admin phải đọc để gửi cho
              // người dùng, còn token nền tảng thì dán vào là xong, không ai cần
              // nhìn lại. Bớt một đường lộ token trên màn hình.
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={dangSua ? t("kenh.tokenGiuNguyen") : undefined}
            />
          )}
        </Truong>
      </div>
    </HopThoai>
  );
}
