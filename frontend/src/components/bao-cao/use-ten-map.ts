"use client";

/**
 * Nạp map `id → tên` cho người dùng và phòng ban, để dịch UUID trần của báo cáo.
 *
 * Vì sao ở đây chứ không join sẵn ở backend: báo cáo #5 cố ý trả UUID (ranh giới
 * module — analytics không import identity). FE tự tra tên.
 *
 * **Không đủ để tra hết, và đó là chấp nhận được** (đo thật): với Manager,
 * `/users` chỉ trả người trong phòng mình, và báo cáo agents còn chứa user
 * `department_id=null` (Admin đã xử lý hội thoại) mà không map nào có. Những id
 * thiếu sẽ hiện mã rút gọn (`tenNguoi`/`tenPhong`), KHÔNG gọi `/users/{id}` vì
 * người ngoài phòng chắc chắn trả 403. Phạm vi do backend lọc theo vai.
 */

import { useQuery } from "@tanstack/react-query";
import {
  khoaQuanTri,
  layDanhSachNguoiDung,
  layDanhSachPhongBan,
} from "@/lib/quan-tri-api";

export interface TenMap {
  nguoi: Map<string, string>;
  phong: Map<string, string>;
  dangTai: boolean;
}

/** limit trần của `/users` là 100 (đã đo) — đủ cho quy mô hiện tại. */
const TRAN_USERS = 100;

export function useTenMap(): TenMap {
  const users = useQuery({
    queryKey: [...khoaQuanTri.nguoiDung.all, "ten-map"],
    queryFn: ({ signal }) =>
      layDanhSachNguoiDung({ limit: TRAN_USERS, offset: 0 }, signal),
  });
  const phong = useQuery({
    queryKey: [...khoaQuanTri.phongBan.all, "ten-map"],
    queryFn: ({ signal }) => layDanhSachPhongBan(signal),
  });

  return {
    nguoi: new Map((users.data?.items ?? []).map((u) => [u.id, u.full_name])),
    phong: new Map((phong.data?.items ?? []).map((p) => [p.id, p.name])),
    dangTai: users.isLoading || phong.isLoading,
  };
}
