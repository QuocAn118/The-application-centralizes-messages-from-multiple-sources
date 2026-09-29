"use client";

/**
 * Đặt mục tiêu KPI (#F3 task 3.2).
 *
 * **RB-3: chỉ có ô `target_value`.** Không có ô nhập thực đạt hay phần trăm —
 * hai giá trị đó lấy từ dữ liệu hội thoại qua `IPerformanceSource`, backend
 * không nhận chúng trong `SetKpiTargetRequest`. Dựng ô nhập cho chúng là mời
 * người dùng gõ một con số rồi vứt đi.
 *
 * **Đặt lại = ghi đè, không phải lỗi trùng.** `SetKpiTarget` tra mục tiêu cũ
 * theo (đối tượng, chỉ số, kỳ) rồi gọi `change_target` nếu đã có — đã xác nhận
 * bằng lời gọi thật: gọi hai lần trả về **cùng `id`** với giá trị mới, status
 * 201 cả hai lần. Nên hộp này dùng chung cho cả "đặt mới" lẫn "sửa", và khi sửa
 * thì khoá phần khoá chính lại để người dùng không tưởng mình đang tạo dòng mới.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { t } from "@/lib/i18n";
import { NHAN_CHI_SO_KPI, NHAN_DOI_TUONG_KPI, DON_VI_KPI, kyKpi } from "@/lib/hien-thi";
import { datMucTieuKpi, khoaNhanSu } from "@/lib/nhan-su-api";
import { xemDuocKpiPhong } from "@/lib/quyen-nhan-su";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import type {
  Department,
  KpiMetricType,
  KpiSubjectType,
  KpiTarget,
  Role,
  UserResponse,
} from "@/lib/types";
import { Truong } from "@/components/ui/truong";
import { OChon, ONhap } from "@/components/ui/o-nhap";

const CHI_SO: KpiMetricType[] = ["CONVERSATIONS_CLOSED", "AVG_RESPONSE_MINUTES"];

export function HopThoaiKpi({
  sua,
  vai,
  nam,
  thang,
  nhanVien,
  phongBan,
  onDong,
}: {
  /** `null` = đặt mục tiêu mới; có giá trị = sửa mục tiêu đã có. */
  sua: KpiTarget | null;
  vai: Role;
  nam: number;
  thang: number;
  /** Nhân viên chọn được — đã lọc theo phạm vi phòng của người thao tác. */
  nhanVien: UserResponse[];
  phongBan: Department[];
  onDong: () => void;
}) {
  const queryClient = useQueryClient();
  const dangSua = sua !== null;

  const [loaiDoiTuong, setLoaiDoiTuong] = useState<KpiSubjectType>(
    sua?.subject_type ?? "USER",
  );
  const [subjectId, setSubjectId] = useState(
    sua?.subject_id ?? nhanVien[0]?.id ?? "",
  );
  const [phongId, setPhongId] = useState(
    sua?.subject_type === "DEPARTMENT"
      ? sua.subject_id
      : (phongBan[0]?.id ?? ""),
  );
  const [chiSo, setChiSo] = useState<KpiMetricType>(
    sua?.metric_type ?? "CONVERSATIONS_CLOSED",
  );
  const [giaTri, setGiaTri] = useState(sua?.target_value.replace(/\.?0+$/, "") ?? "");

  // Staff không đặt được mục tiêu nên không tới đây; nhưng Manager cũng chỉ áp
  // được cho phòng mình, và ô chọn phòng của họ chỉ có một lựa chọn.
  const chonDuocPhong = xemDuocKpiPhong(vai);

  const doiTuongDangChon = loaiDoiTuong === "USER" ? subjectId : phongId;
  // `Field(ge=0)` ở backend — chặn số âm tại đây kèm câu giải thích thay vì để
  // nhận 422 với thông điệp của pydantic.
  const soHopLe = giaTri.trim() !== "" && Number(giaTri) >= 0 && Number.isFinite(Number(giaTri));
  const hopLe = soHopLe && doiTuongDangChon !== "";

  const luu = useMutation({
    mutationFn: () =>
      datMucTieuKpi({
        subject_type: loaiDoiTuong,
        subject_id: doiTuongDangChon,
        metric_type: chiSo,
        period_year: nam,
        period_month: thang,
        target_value: giaTri.trim(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: khoaNhanSu.kpi.all });
      onDong();
    },
  });

  return (
    <HopThoai
      tieuDe={dangSua ? t("kpi.suaMucTieu") : t("kpi.datMucTieu")}
      moTa={kyKpi(nam, thang)}
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
        {/* Khi sửa, khoá chính (đối tượng + chỉ số) hiện chỉ-đọc: đổi chúng
            không "sửa" dòng này mà tạo/ghi đè một mục tiêu KHÁC — dễ hiểu nhầm
            thành đang đổi tên dòng đang đứng. */}
        {dangSua ? (
          <dl className="rounded-nb border-2 border-line bg-sunken px-3 py-2.5">
            <dt className="text-xs font-bold uppercase tracking-wide text-ink-2">
              {NHAN_DOI_TUONG_KPI[sua.subject_type]}
            </dt>
            <dd className="mt-1 text-sm font-semibold text-ink">{NHAN_CHI_SO_KPI[sua.metric_type]}</dd>
          </dl>
        ) : (
          <>
            {chonDuocPhong && (
              <Truong nhan={t("kpi.loaiDoiTuong")}>
                {(o) => (
                  <OChon
                    {...o}
                    value={loaiDoiTuong}
                    onChange={(e) => setLoaiDoiTuong(e.target.value as KpiSubjectType)}
                  >
                    <option value="USER">{NHAN_DOI_TUONG_KPI.USER}</option>
                    <option value="DEPARTMENT">{NHAN_DOI_TUONG_KPI.DEPARTMENT}</option>
                  </OChon>
                )}
              </Truong>
            )}

            {loaiDoiTuong === "USER" ? (
              <Truong
                nhan={t("kpi.chonNhanVien")}
                loi={nhanVien.length === 0 ? t("kpi.khongCoNhanVien") : null}
              >
                {(o) => (
                  <OChon
                    {...o}
                    value={subjectId}
                    onChange={(e) => setSubjectId(e.target.value)}
                    disabled={nhanVien.length === 0}
                  >
                    {nhanVien.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name}
                      </option>
                    ))}
                  </OChon>
                )}
              </Truong>
            ) : (
              <Truong nhan={t("kpi.chonPhong")}>
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

            <Truong nhan={t("kpi.chiSo")}>
              {(o) => (
                <OChon {...o} value={chiSo} onChange={(e) => setChiSo(e.target.value as KpiMetricType)}>
                  {CHI_SO.map((c) => (
                    <option key={c} value={c}>
                      {NHAN_CHI_SO_KPI[c]}
                    </option>
                  ))}
                </OChon>
              )}
            </Truong>
          </>
        )}

        <Truong
          nhan={`${t("kpi.giaTriMucTieu")} (${DON_VI_KPI[dangSua ? sua.metric_type : chiSo]})`}
          batBuoc
          loi={giaTri.trim() !== "" && !soHopLe ? t("kpi.giaTriPhaiDuong") : null}
        >
          {(o) => (
            <ONhap
              {...o}
              type="number"
              min={0}
              step="0.01"
              value={giaTri}
              onChange={(e) => setGiaTri(e.target.value)}
              className="tabular-nums"
            />
          )}
        </Truong>

        {/* RB-3 nói thẳng cho người dùng, không chỉ nằm trong mã. */}
        <p className="rounded-nb border-2 border-line bg-sunken px-3 py-2.5 text-xs text-ink-2">
          {t("kpi.ghiChuThucDat")}
          {!dangSua && ` ${t("kpi.deDatLai")}`}
        </p>
      </div>
    </HopThoai>
  );
}
