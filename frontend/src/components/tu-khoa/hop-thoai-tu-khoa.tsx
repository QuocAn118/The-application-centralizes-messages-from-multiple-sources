"use client";

/**
 * Tạo / sửa một từ khoá (#F4 task 1.3).
 *
 * **RB-3: KHÔNG tự đoán trùng ở FE.** Backend chuẩn hoá bằng `chuan_hoa()` (bỏ
 * dấu tiếng Việt, thường hoá, gộp khoảng trắng) rồi chặn trùng theo dạng đã
 * chuẩn hoá — đã xác nhận bằng lời gọi thật: `"Bảo Hành"`, `"bao hanh"` và
 * `"  Bảo    Hành  "` đều cho 409 `KEYWORD_DUPLICATE`.
 *
 * Viết lại hàm bỏ dấu ở đây để báo trùng sớm là chép một thuật toán tinh tế
 * (`unicodedata` NFD + xử lý riêng `đ`/`Đ`) sang chỗ thứ hai, rồi hai bản lệch
 * nhau lúc nào không biết. Gửi đi, nhận 409, hiện thẳng thông điệp server.
 *
 * **RB-6:** `PATCH` chỉ nhận `text` — không đổi được phòng. Khi sửa thì phòng
 * hiện chỉ-đọc.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { khoaTuKhoa, suaTuKhoa, taoTuKhoa } from "@/lib/tu-khoa-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { Truong } from "@/components/ui/truong";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import type { Department, Keyword } from "@/lib/types";

/** Trùng `max_length=200` của `CreateKeywordRequest`. */
const DAI_TOI_DA = 200;

export function HopThoaiTuKhoa({
  tuKhoa,
  phongBan,
  phongMacDinh,
  onDong,
}: {
  /** `null` = thêm mới. */
  tuKhoa: Keyword | null;
  /** Phòng được phép chọn. Manager chỉ có một; Admin có tất cả. */
  phongBan: Department[];
  phongMacDinh: string;
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const dangSua = tuKhoa !== null;

  const [text, setText] = useState(tuKhoa?.text ?? "");
  const [phongId, setPhongId] = useState(tuKhoa?.department_id ?? phongMacDinh);

  // `min_length=1` ở backend — chặn tại chỗ vì biết trước sẽ 422.
  const hopLe = text.trim().length > 0 && phongId !== "";

  const luu = useMutation({
    mutationFn: () =>
      tuKhoa
        ? suaTuKhoa(tuKhoa.id, text.trim())
        : taoTuKhoa({ department_id: phongId, text: text.trim() }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaTuKhoa.tuKhoa.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={dangSua ? t("tuKhoa.suaTieuDe") : t("tuKhoa.them")}
      moTa={dangSua ? tuKhoa.text : undefined}
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
      <div className="mt-4 flex flex-col gap-4">
        {/* Phòng KHÔNG sửa được: `UpdateKeywordRequest` chỉ có `text`. Hiện
            chỉ-đọc thay vì ô chọn, như mẫu ca ở #F3. */}
        {dangSua ? (
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-ink">{t("tuKhoa.phongBan")}</span>
            <p className="text-sm text-ink">
              {phongBan.find((p) => p.id === tuKhoa.department_id)?.name ??
                t("nguoiDung.khongPhong")}
            </p>
          </div>
        ) : (
          <Truong nhan={t("tuKhoa.phongBan")}>
            {(o) => (
              <OChon {...o} value={phongId} onChange={(e) => setPhongId(e.target.value)}>
                {phongBan.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </OChon>
            )}
          </Truong>
        )}

        {/* Giải thích chuẩn hoá NGAY dưới ô: người dùng gõ "bao hanh" rồi nhận
            "đã tồn tại" mà không hiểu vì sao sẽ tưởng hệ thống hỏng. Khi sửa,
            kèm dạng khớp hiện tại (T2: nơi thứ hai được hiện dạng khớp). */}
        <Truong
          nhan={t("tuKhoa.noiDung")}
          batBuoc
          goiY={
            dangSua
              ? `${t("tuKhoa.dangKhop", { chuan: tuKhoa.normalized })}. ${t("tuKhoa.giaiThichChuanHoa")}`
              : t("tuKhoa.giaiThichChuanHoa")
          }
        >
          {(o) => (
            <ONhap
              {...o}
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={DAI_TOI_DA}
              autoFocus
            />
          )}
        </Truong>
      </div>
    </HopThoai>
  );
}
