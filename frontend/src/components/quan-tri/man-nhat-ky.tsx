"use client";

/**
 * Màn Nhật ký (#F2 GĐ4; redesign Phần 6 Q4) — chỉ Admin.
 *
 * **RB-8: chỉ đọc.** Entity `AuditLog` cố ý không có phương thức sửa/xoá, nên
 * màn này không có nút ghi nào. Có một dòng nói rõ điều đó để người dùng không
 * đi tìm nút xoá.
 *
 * Tên người thực hiện và **tên đối tượng** (Q4): nhật ký chỉ trả UUID, nên tra
 * ngược sang danh sách người dùng + phòng ban đã tải sẵn (giống màn Báo cáo),
 * UUID chuyển vào tooltip. Không gọi `GET /users/{id}` cho từng dòng — 25 dòng
 * là 25 lời gọi, mà phần lớn trỏ tới cùng vài người. Không tra được (ngoài 100
 * người đầu, hoặc đã xoá) → mã rút gọn 8 ký tự, UUID đủ vẫn ở tooltip.
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollText, X } from "lucide-react";
import { t } from "@/lib/i18n";
import { NHAN_HANH_DONG, lopBadgeHanhDong, mocDayDu } from "@/lib/hien-thi";
import {
  KICH_THUOC_TRANG,
  khoaQuanTri,
  layDanhSachNguoiDung,
  layDanhSachPhongBan,
  layNhatKy,
  type ThamSoNhatKy,
} from "@/lib/quan-tri-api";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { OChon, ONhap } from "@/components/ui/o-nhap";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { GoiY } from "@/components/ui/goi-y";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import type { AuditAction } from "@/lib/types";

/** Nhóm hành động cho ô chọn, theo đúng tiền tố backend dùng. */
const NHOM: { nhan: string; loai: string }[] = [
  { nhan: t("nhatKy.loaiUser"), loai: "user" },
  { nhan: t("nhatKy.loaiDepartment"), loai: "department" },
  { nhan: t("nhatKy.loaiAuth"), loai: "auth" },
];
const NHAN_LOAI = new Map(NHOM.map((n) => [n.loai, n.nhan]));

const MOI_HANH_DONG = Object.keys(NHAN_HANH_DONG) as AuditAction[];

export function ManNhatKy() {
  const [thamSo, setThamSo] = useState<ThamSoNhatKy>({
    limit: KICH_THUOC_TRANG,
    offset: 0,
  });

  const truyVan = useQuery({
    queryKey: [...khoaQuanTri.nhatKy.all, thamSo],
    queryFn: ({ signal }) => layNhatKy(thamSo, signal),
  });

  // Tải một lần danh sách người dùng + phòng ban để tra tên theo UUID.
  const truyVanNguoiDung = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "tra-ten"],
    queryFn: ({ signal }) => layDanhSachNguoiDung({ limit: 100, offset: 0 }, signal),
  });
  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  const tenTheoId = useMemo(
    () =>
      new Map<string, string>([
        ...(truyVanNguoiDung.data?.items ?? []).map((u) => [u.id, u.full_name] as const),
        ...(truyVanPhongBan.data?.items ?? []).map((p) => [p.id, p.name] as const),
      ]),
    [truyVanNguoiDung.data, truyVanPhongBan.data],
  );

  function doiThamSo(phan: Partial<ThamSoNhatKy>) {
    setThamSo((truoc) => ({ ...truoc, ...phan, offset: 0 }));
  }

  const trang = truyVan.data;
  const coLoc =
    thamSo.action !== undefined ||
    thamSo.resource_type !== undefined ||
    thamSo.from_time !== undefined ||
    thamSo.to_time !== undefined;

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang tieuDe={t("nhatKy.tieuDe")} moTa={t("nhatKy.chiDoc")} />

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          {t("nhatKy.locHanhDong")}
          <OChon
            className="w-64"
            value={thamSo.action ?? ""}
            onChange={(e) => doiThamSo({ action: (e.target.value || undefined) as AuditAction | undefined })}
          >
            <option value="">{t("quanTri.tatCa")}</option>
            {MOI_HANH_DONG.map((hd) => (
              <option key={hd} value={hd}>
                {NHAN_HANH_DONG[hd]}
              </option>
            ))}
          </OChon>
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          {t("nhatKy.locLoaiDoiTuong")}
          <OChon
            className="w-44"
            value={thamSo.resource_type ?? ""}
            onChange={(e) => doiThamSo({ resource_type: e.target.value || undefined })}
          >
            <option value="">{t("quanTri.tatCa")}</option>
            {NHOM.map((n) => (
              <option key={n.loai} value={n.loai}>
                {n.nhan}
              </option>
            ))}
          </OChon>
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          {t("nhatKy.locTuNgay")}
          <ONhap
            type="date"
            className="w-44"
            value={thamSo.from_time?.slice(0, 10) ?? ""}
            onChange={(e) =>
              doiThamSo({
                // Ô `date` cho ra "2026-09-16"; backend nhận datetime nên gắn
                // đầu ngày. Không dùng `new Date(...)`: nó diễn giải chuỗi
                // trần là UTC và ngày sẽ lệch với người ở múi giờ khác.
                from_time: e.target.value ? `${e.target.value}T00:00:00` : undefined,
              })
            }
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
          {t("nhatKy.locDenNgay")}
          <ONhap
            type="date"
            className="w-44"
            value={thamSo.to_time?.slice(0, 10) ?? ""}
            onChange={(e) =>
              doiThamSo({
                // Cuối ngày, không phải đầu ngày: chọn "đến 16/09" mà gửi
                // 00:00 thì mất hết bản ghi của chính ngày 16.
                to_time: e.target.value ? `${e.target.value}T23:59:59` : undefined,
              })
            }
          />
        </label>
        {coLoc && (
          <Nut bienThe="trong" icon={X} onClick={() => setThamSo({ limit: KICH_THUOC_TRANG, offset: 0 })}>
            {t("nhatKy.xoaLoc")}
          </Nut>
        )}
      </div>

      {truyVan.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVan.isError && (
        <The>
          <TrangThaiLoi thongDiep={thongDiepLoi(truyVan.error)} onThuLai={() => void truyVan.refetch()} />
        </The>
      )}
      {trang && trang.items.length === 0 && (
        <The>
          <TrangThaiRong icon={ScrollText} tieuDe={t("quanTri.trong")} />
        </The>
      )}
      {trang && trang.items.length > 0 && (
        <div className="flex flex-col gap-3">
          <Bang aria-label={t("nhatKy.tieuDe")}>
            <thead>
              <tr>
                <Th className="w-44">{t("nhatKy.cotThoiGian")}</Th>
                <Th className="w-64">{t("nhatKy.cotHanhDong")}</Th>
                <Th className="w-52">{t("nhatKy.cotNguoiThucHien")}</Th>
                <Th>{t("nhatKy.cotDoiTuong")}</Th>
              </tr>
            </thead>
            <tbody>
              {trang.items.map((dong) => (
                <Tr key={dong.id}>
                  <Td className="whitespace-nowrap text-xs text-ink-2">{mocDayDu(dong.created_at)}</Td>
                  <Td>
                    <HuyHieu lop={lopBadgeHanhDong(dong.action)}>{NHAN_HANH_DONG[dong.action]}</HuyHieu>
                  </Td>
                  <Td>
                    {dong.actor_id
                      ? // Người thực hiện có thể không nằm trong 100 người đã tải;
                        // khi đó "Không rõ" thay vì UUID trần.
                        (tenTheoId.get(dong.actor_id) ?? t("nhatKy.khongRo"))
                      : // `actor_id` rỗng = hệ thống tự làm (ví dụ đăng nhập
                        // thất bại: chưa biết là ai).
                        <span className="text-ink-2">{t("nhatKy.heThong")}</span>}
                  </Td>
                  <Td>
                    <span className="text-xs font-bold uppercase tracking-wide text-ink-2">
                      {NHAN_LOAI.get(dong.resource_type) ?? dong.resource_type}
                    </span>
                    {dong.resource_id && (
                      <GoiY noiDung={<span className="font-mono">{dong.resource_id}</span>}>
                        <span
                          tabIndex={0}
                          className="block w-fit cursor-help font-semibold text-ink underline decoration-dotted underline-offset-2"
                        >
                          {tenTheoId.get(dong.resource_id) ?? (
                            <span className="font-mono">#{dong.resource_id.slice(0, 8)}</span>
                          )}
                        </span>
                      </GoiY>
                    )}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Bang>
          <ThanhPhanTrang
            offset={trang.offset}
            limit={trang.limit}
            total={trang.total}
            dangTai={truyVan.isFetching}
            doiOffset={(offsetMoi) => setThamSo((truoc) => ({ ...truoc, offset: offsetMoi }))}
          />
        </div>
      )}
    </div>
  );
}
