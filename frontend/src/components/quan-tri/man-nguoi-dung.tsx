"use client";

/**
 * Màn Người dùng (#F2 GĐ1).
 *
 * Giữ toàn bộ trạng thái lọc + hộp thoại đang mở ở đây, còn bảng và bộ lọc là
 * component thuần nhận props. Gom vậy để chỉ có MỘT chỗ biết "đang mở hộp thoại
 * nào cho ai" — mở hai hộp chồng nhau là lỗi rất khó nhìn ra khi trạng thái
 * nằm rải rác.
 */

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { UserPlus, Users } from "lucide-react";
import { t } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import {
  KICH_THUOC_TRANG,
  khoaQuanTri,
  layDanhSachNguoiDung,
  layDanhSachPhongBan,
} from "@/lib/quan-tri-api";
import { hienTaoTaiKhoan, type NguoiThaoTac } from "@/lib/quyen-quan-tri";
import { thongDiepLoi } from "@/lib/loi-quan-tri";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import { DauTrang } from "@/components/ui/dau-trang";
import { The } from "@/components/ui/the";
import { Nut } from "@/components/ui/nut";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import { BoLocNguoiDung } from "./bo-loc-nguoi-dung";
import { BangNguoiDung, type ThaoTac } from "./bang-nguoi-dung";
import { HopThoaiTaoNguoiDung } from "./hop-thoai-tao-nguoi-dung";
import { HopThoaiSuaHoSo } from "./hop-thoai-sua-ho-so";
import { HopThoaiDoiVaiTro } from "./hop-thoai-doi-vai-tro";
import { HopThoaiDoiPhongBan } from "./hop-thoai-doi-phong-ban";
import { HopThoaiDatLaiMatKhau } from "./hop-thoai-dat-lai-mat-khau";
import { HopXacNhanTrangThai } from "./hop-xac-nhan-trang-thai";
import type { ThamSoNguoiDung, UserResponse } from "@/lib/types";

/** Hộp thoại đang mở — `null` là không mở gì. */
type DangMo =
  | { loai: "tao" }
  | { loai: ThaoTac; nguoi: UserResponse }
  | null;

export function ManNguoiDung() {
  const { user } = useAuth();
  const [thamSo, setThamSo] = useState<ThamSoNguoiDung>({
    limit: KICH_THUOC_TRANG,
    offset: 0,
  });
  const [dangMo, setDangMo] = useState<DangMo>(null);

  const actor: NguoiThaoTac | null = useMemo(
    () =>
      user
        ? { id: user.id, role: user.role, department_id: user.department_id }
        : null,
    [user],
  );

  const truyVanNguoiDung = useQuery({
    queryKey: khoaQuanTri.nguoiDung.list(thamSo),
    queryFn: ({ signal }) => layDanhSachNguoiDung(thamSo, signal),
  });

  // Tên phòng ban dùng ở cả cột "Phòng ban", bộ lọc và hai hộp thoại — tải một
  // lần ở đây rồi truyền xuống, thay vì mỗi nơi tự gọi.
  const truyVanPhongBan = useQuery({
    queryKey: khoaQuanTri.phongBan.all,
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  if (!actor) return null;

  const phongBan = truyVanPhongBan.data?.items ?? [];
  const trang = truyVanNguoiDung.data;

  /** Đổi bộ lọc luôn kéo về trang đầu — không thì có thể rơi vào trang trống. */
  function doiThamSo(phan: Partial<ThamSoNguoiDung>) {
    setThamSo((truoc) => ({ ...truoc, ...phan, offset: 0 }));
  }

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-8 py-6">
      <DauTrang
        tieuDe={t("nguoiDung.tieuDe")}
        moTa={
          actor.role === "ADMIN"
            ? "Tài khoản của mọi phòng: vai trò, phòng ban, trạng thái."
            : "Nhân viên trong phòng của bạn."
        }
        hanhDong={
          hienTaoTaiKhoan(actor) && (
            <Nut bienThe="chinh" icon={UserPlus} onClick={() => setDangMo({ loai: "tao" })}>
              {t("nguoiDung.taoMoi")}
            </Nut>
          )
        }
      />

      <BoLocNguoiDung vai={actor.role} thamSo={thamSo} phongBan={phongBan} doiThamSo={doiThamSo} />

      {truyVanNguoiDung.isPending && (
        <The>
          <TrangThaiTai />
        </The>
      )}
      {truyVanNguoiDung.isError && (
        <The>
          <TrangThaiLoi
            thongDiep={thongDiepLoi(truyVanNguoiDung.error)}
            onThuLai={() => void truyVanNguoiDung.refetch()}
          />
        </The>
      )}
      {trang && trang.items.length === 0 && (
        <The>
          <TrangThaiRong icon={Users} tieuDe={t("quanTri.trong")} moTa="Thử bỏ bớt bộ lọc hoặc đổi từ khoá tìm." />
        </The>
      )}
      {trang && trang.items.length > 0 && (
        <div className="flex flex-col gap-3">
          <BangNguoiDung
            danhSach={trang.items}
            phongBan={phongBan}
            actor={actor}
            chonThaoTac={(thaoTac, nguoi) => setDangMo({ loai: thaoTac, nguoi })}
          />
          <ThanhPhanTrang
            offset={trang.offset}
            limit={trang.limit}
            total={trang.total}
            dangTai={truyVanNguoiDung.isFetching}
            doiOffset={(offsetMoi) => setThamSo((truoc) => ({ ...truoc, offset: offsetMoi }))}
          />
        </div>
      )}

      {dangMo?.loai === "tao" && (
        <HopThoaiTaoNguoiDung
          phongBan={phongBan}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "suaHoSo" && (
        <HopThoaiSuaHoSo nguoi={dangMo.nguoi} onDong={() => setDangMo(null)} />
      )}
      {dangMo?.loai === "doiVaiTro" && (
        <HopThoaiDoiVaiTro
          nguoi={dangMo.nguoi}
          phongBan={phongBan}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "doiPhongBan" && (
        <HopThoaiDoiPhongBan
          nguoi={dangMo.nguoi}
          phongBan={phongBan}
          onDong={() => setDangMo(null)}
        />
      )}
      {dangMo?.loai === "datLaiMatKhau" && (
        <HopThoaiDatLaiMatKhau
          nguoi={dangMo.nguoi}
          onDong={() => setDangMo(null)}
        />
      )}
      {(dangMo?.loai === "voHieuHoa" || dangMo?.loai === "kichHoatLai") && (
        <HopXacNhanTrangThai
          nguoi={dangMo.nguoi}
          voHieuHoa={dangMo.loai === "voHieuHoa"}
          onDong={() => setDangMo(null)}
        />
      )}
    </div>
  );
}
