"use client";

/**
 * Nội dung trang `/design-system`: mọi token, component và trạng thái của design
 * system Neo-Brutalism, với dữ liệu giả có đủ dấu tiếng Việt để kiểm hiển thị.
 */

import { useState, useSyncExternalStore } from "react";
import {
  Ban,
  Inbox,
  Pencil,
  Plus,
  Power,
  Save,
  Send,
  Trash2,
  UserPlus,
} from "lucide-react";
import { HopThoai, NutChinh, NutPhu } from "@/components/hop-thoai";
import { HopXacNhan } from "@/components/hop-xac-nhan";
import { OTimKiem } from "@/components/o-tim-kiem";
import { ThanhPhanTrang } from "@/components/thanh-phan-trang";
import { BadgeKenh, BadgeTrangThai } from "@/components/badges";
import { Avatar } from "@/components/ui/avatar";
import { Bang, Td, Th, Tr } from "@/components/ui/bang";
import { DauTrang } from "@/components/ui/dau-trang";
import { HuyHieu } from "@/components/ui/huy-hieu";
import { IconKenh } from "@/components/ui/icon-kenh";
import { MenuHanhDong } from "@/components/ui/menu-hanh-dong";
import { Nut } from "@/components/ui/nut";
import { NutIcon } from "@/components/ui/nut-icon";
import { ONhap, OChon, VungNhap } from "@/components/ui/o-nhap";
import { TabKhu } from "@/components/ui/tab-khu";
import { The, TheDau } from "@/components/ui/the";
import { TrangThaiLoi, TrangThaiRong, TrangThaiTai } from "@/components/ui/trang-thai";
import { Truong } from "@/components/ui/truong";
import { BAN_MAU } from "@/components/ui/ban-mau";
import { DAU_GACH } from "@/lib/hien-thi";
import { tuongPhan } from "@/lib/tuong-phan";
import type { Platform } from "@/lib/types";

const KENH: Platform[] = ["ZALO", "FACEBOOK", "INSTAGRAM", "TELEGRAM"];

/** [token chữ, token nền, ngưỡng] để hiện tỉ lệ tương phản thật. */
const CAP_MAU: [string, string, number][] = [
  ["ink", "paper", 4.5],
  ["ink-2", "paper", 4.5],
  ["ink-2", "sunken", 4.5],
  ["ink", "accent", 4.5],
  ["card", "accent-2", 4.5],
  ["ok", "ok-bg", 4.5],
  ["wait", "wait-bg", 4.5],
  ["bad", "bad-bg", 4.5],
];

const MAU_NEN = ["paper", "card", "sunken", "ink", "ink-2", "line", "accent", "accent-2"];

const KHACH = [
  { id: "019fd148-249d-7a53-8ed4-24b7723d94fd", ten: "Nguyễn Thị Mai Anh", kenh: "ZALO" as Platform },
  { id: "01a0a317-92c1-70e3-803c-b2a3aa793727", ten: "Trần Quốc Việt", kenh: "TELEGRAM" as Platform },
  { id: "01a0a486-e024-7b90-be31-ce95d4d92852", ten: "Đỗ Hải Yến", kenh: "INSTAGRAM" as Platform },
  { id: "01a0a48b-e241-7821-83b9-dde12e5878a9", ten: "Phạm Đức Thắng", kenh: "FACEBOOK" as Platform },
  { id: "01a0a06a-bff2-7202-a6f4-082bbd6ff371", ten: null, kenh: "TELEGRAM" as Platform },
];

function Muc({ tieuDe, children }: { tieuDe: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="border-b-2 border-ink pb-2 text-lg font-bold text-ink">{tieuDe}</h2>
      {children}
    </section>
  );
}

/**
 * Đọc hex thật của token từ CSS đang chạy (không chép giá trị vào đây).
 * `useSyncExternalStore`: server trả rỗng, client đọc một lần rồi giữ trong bộ
 * nhớ — không cần effect + setState, không lệch hydrate.
 */
const RONG: Record<string, string> = {};
let daDoc: Record<string, string> | null = null;

function docToken(): Record<string, string> {
  if (!daDoc) {
    const s = getComputedStyle(document.documentElement);
    const ten = [...new Set([...MAU_NEN, ...CAP_MAU.flatMap(([a, b]) => [a, b])])];
    daDoc = Object.fromEntries(ten.map((n) => [n, s.getPropertyValue(`--${n}`).trim()]));
  }
  return daDoc;
}

function useToken(): Record<string, string> {
  return useSyncExternalStore(
    () => () => {},
    docToken,
    () => RONG,
  );
}

export function TrangMau() {
  const token = useToken();
  const [hop, setHop] = useState<"thuong" | "khongDong" | "xacNhan" | null>(null);
  const [offset, setOffset] = useState(0);

  return (
    <div className="min-h-screen bg-paper">
      <TabKhu
        tieuDe="Design system"
        tab={[
          { duongDan: "/design-system", nhan: "Thành phần" },
          { duongDan: "/inbox", nhan: "Về app" },
        ]}
      />

      <main className="mx-auto flex max-w-[1280px] flex-col gap-12 px-8 py-8">
        <DauTrang
          tieuDe="Neo-Brutalism cho OmniChat"
          moTa="Trang chỉ có ở môi trường dev. Mọi thành phần dưới đây là thành phần thật mà các màn sẽ dùng."
          hanhDong={
            <Nut bienThe="chinh" icon={Plus}>
              Nút chính của trang
            </Nut>
          }
        />

        <Muc tieuDe="Màu và tương phản (đọc từ CSS đang chạy)">
          <div className="grid grid-cols-8 gap-3">
            {MAU_NEN.map((n) => (
              <div key={n} className="flex flex-col gap-1.5">
                <div
                  className="h-16 rounded-nb border-2 border-ink"
                  style={{ background: `var(--${n})` }}
                />
                <span className="text-xs font-bold text-ink">{n}</span>
                <span className="font-mono text-xs text-ink-2">{token[n]}</span>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-3">
            {CAP_MAU.map(([chu, nen, nguong]) => {
              const tl = token[chu] && token[nen] ? tuongPhan(token[chu], token[nen]) : 0;
              return (
                <div
                  key={`${chu}-${nen}`}
                  className="flex items-center justify-between rounded-nb border-2 border-ink px-3 py-2.5"
                  style={{ background: `var(--${nen})`, color: `var(--${chu})` }}
                >
                  <span className="text-sm font-semibold">
                    {chu} / {nen}
                  </span>
                  <span className="font-mono text-sm font-bold tabular-nums">
                    {tl ? `${tl.toFixed(1)}:1` : "…"} {tl >= nguong ? "đạt" : ""}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-sm font-semibold text-ink">
              Bảng 8 màu dịu: nhãn khách, màu ca, nền avatar (nhãn chỉ được chọn trong bảng này)
            </p>
            <div className="flex gap-3">
              {BAN_MAU.map((lop, i) => (
                <span
                  key={lop}
                  className={`${lop} inline-flex h-10 items-center rounded-nb border-2 border-ink px-3 text-sm font-bold text-ink`}
                >
                  Nhãn {i + 1}
                </span>
              ))}
            </div>
          </div>
        </Muc>

        <Muc tieuDe="Chữ (Be Vietnam Pro, kiểm dấu tiếng Việt)">
          <div className="flex flex-col gap-3">
            <p className="text-[28px] font-extrabold leading-tight tracking-tight text-ink">
              Tiêu đề trang 28/800: Hộp thư của phòng Kỹ thuật
            </p>
            <p className="text-lg font-bold text-ink">Tiêu đề mục 18/700: Lịch phân ca tuần này</p>
            <p className="text-sm text-ink">
              Nội dung 14/400: Quý khách đã được chuyển sang phòng Kỹ thuật lúc 14:32. Nhân viên
              phụ trách sẽ phản hồi trong ít phút nữa.
            </p>
            <p className="text-sm text-ink-2">
              Chữ phụ 14/400: Cập nhật lần cuối bởi Nguyễn Thị Mai Anh, hôm qua.
            </p>
            <p className="text-xs font-semibold text-ink-2">
              Chữ nhỏ 12/600: Ảnh, đơn từ, khuyến mãi, bảo hành, sửa chữa, lỗi kết nối.
            </p>
            <p className="text-sm text-ink">
              Dấu đủ bộ: ă â đ ê ô ơ ư · á à ả ã ạ · Ắ Ằ Ẳ Ẵ Ặ · Ố Ồ Ổ Ỗ Ộ · Ứ Ừ Ử Ữ Ự · Ý Ỳ Ỷ Ỹ Ỵ
            </p>
            <p className="text-sm tabular-nums text-ink">Số: 1.234 tin vào · 98 hội thoại · 12 phút</p>
          </div>
        </Muc>

        <Muc tieuDe="Quy tắc bóng">
          <div className="grid grid-cols-3 gap-6">
            <div className="flex flex-col gap-3 rounded-nb border-2 border-ink bg-card p-4 shadow-nb">
              <p className="text-sm font-bold text-ink">1. Nút: bóng nhỏ + phản hồi</p>
              <p className="text-sm text-ink-2">Rê thì dịch 2px, nhấn thì dịch hết và bóng về 0. Bóng kèm phản hồi nghĩa là bấm được.</p>
              <div><Nut bienThe="chinh" co="sm">Thử rê và nhấn</Nut></div>
            </div>
            <div className="flex flex-col gap-3 rounded-nb border-2 border-ink bg-card p-4 shadow-nb">
              <p className="text-sm font-bold text-ink">2. Card, bảng, khung: bóng làm khung</p>
              <p className="text-sm text-ink-2">Bóng 4px đánh dấu khối nổi của trang (thẻ, bảng, hộp thoại, menu). Không phản hồi khi rê hay nhấn.</p>
            </div>
            <div className="flex flex-col gap-3 rounded-nb border-2 border-ink bg-card p-4 shadow-nb">
              <p className="text-sm font-bold text-ink">3. Huy hiệu: không bóng</p>
              <p className="text-sm text-ink-2">Nhãn trạng thái không có bóng, nhờ vậy không ai nhầm nó với nút.</p>
              <div className="flex gap-2"><HuyHieu tong="ok">Đang dùng</HuyHieu><HuyHieu tong="wait">Chờ duyệt</HuyHieu></div>
            </div>
          </div>
        </Muc>

        <Muc tieuDe="Nút (bóng nhỏ + phản hồi khi rê/nhấn)">
          <div className="flex flex-wrap items-center gap-3">
            <Nut bienThe="chinh" icon={Send}>
              Gửi trả lời
            </Nut>
            <Nut bienThe="phu" icon={UserPlus}>
              Nhận việc
            </Nut>
            <Nut bienThe="nguyHiem" icon={Trash2}>
              Xoá từ khoá
            </Nut>
            <Nut bienThe="trong" icon={Pencil}>
              Sửa
            </Nut>
            <Nut bienThe="chinh" dangChay>
              Đang lưu
            </Nut>
            <Nut bienThe="chinh" disabled>
              Gửi (vô hiệu)
            </Nut>
            <Nut bienThe="phu" disabled>
              Trước (vô hiệu)
            </Nut>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Nut bienThe="chinh" co="sm" icon={Save}>
              Lưu nhỏ
            </Nut>
            <Nut bienThe="phu" co="sm">
              Huỷ nhỏ
            </Nut>
            <NutIcon icon={Pencil} nhan="Sửa ca làm việc" />
            <NutIcon icon={Power} nhan="Ngừng dùng" bienThe="phu" />
            <NutChinh>NutChinh (API cũ)</NutChinh>
            <NutPhu>NutPhu (API cũ)</NutPhu>
            <NutChinh nguyHiem>NutChinh nguy hiểm</NutChinh>
          </div>
          <p className="text-sm text-ink-2">
            Mô phỏng trạng thái (để nhìn cả ba cùng lúc):
          </p>
          <div className="flex items-center gap-6">
            <Nut bienThe="chinh">Thường</Nut>
            <Nut bienThe="chinh" className="translate-x-[2px] translate-y-[2px] !shadow-nb-sm">
              Đang rê
            </Nut>
            <Nut bienThe="chinh" className="translate-x-[4px] translate-y-[4px] !shadow-none">
              Đang nhấn
            </Nut>
            <Nut bienThe="chinh" className="outline-3 outline-offset-2 outline-accent-2">
              Focus bàn phím
            </Nut>
          </div>
        </Muc>

        <Muc tieuDe="Ô nhập (nhãn trên, gợi ý và lỗi dưới)">
          <div className="grid grid-cols-3 gap-6">
            <Truong nhan="Tên khách" goiY="Tên hiển thị trên nền tảng." batBuoc>
              {(o) => <ONhap {...o} defaultValue="Nguyễn Thị Mai Anh" />}
            </Truong>
            <Truong nhan="Từ khoá" loi="Từ khoá này đã tồn tại trong phòng (dạng khớp: bao hanh).">
              {(o) => <ONhap {...o} defaultValue="Bảo Hành" />}
            </Truong>
            <Truong nhan="Phòng ban">
              {(o) => (
                <OChon {...o} defaultValue="kt">
                  <option value="kd">Phòng Kinh doanh</option>
                  <option value="kt">Phòng Kỹ thuật</option>
                  <option value="cs">Phòng Chăm sóc khách hàng</option>
                </OChon>
              )}
            </Truong>
            <Truong nhan="Lý do từ chối" goiY="Người gửi đơn sẽ thấy lý do này.">
              {(o) => <VungNhap {...o} placeholder="Nhập lý do…" />}
            </Truong>
            <Truong nhan="Email (vô hiệu)">
              {(o) => <ONhap {...o} disabled defaultValue="mai.anh@congty.vn" />}
            </Truong>
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-semibold text-ink">Ô tìm (OTimKiem)</span>
              <OTimKiem nhanGoiY="Tìm theo tên khách…" doiTuKhoa={() => {}} />
            </div>
          </div>
        </Muc>

        <Muc tieuDe="Huy hiệu (không bóng), logo kênh, avatar">
          <div className="flex flex-wrap items-center gap-3">
            <HuyHieu tong="ok">Đang dùng</HuyHieu>
            <HuyHieu tong="wait">Chờ duyệt</HuyHieu>
            <HuyHieu tong="bad">Từ chối</HuyHieu>
            <HuyHieu tong="info">Quản lý</HuyHieu>
            <HuyHieu>Đã ngừng</HuyHieu>
            <BadgeTrangThai status="CHO_PHAN" />
            <BadgeTrangThai status="DANG_MO" />
            <BadgeTrangThai status="DA_DONG" />
          </div>
          <div className="flex flex-wrap items-center gap-6">
            {KENH.map((k) => (
              <span key={k} className="inline-flex items-center gap-3">
                <IconKenh kenh={k} co={20} />
                <BadgeKenh platform={k} />
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-6">
            {KHACH.map((k) => (
              <span key={k.id} className="inline-flex items-center gap-3">
                <Avatar id={k.id} ten={k.ten} kenh={k.kenh} />
                <span className="text-sm font-semibold text-ink">{k.ten ?? "Khách chưa rõ tên"}</span>
              </span>
            ))}
          </div>
        </Muc>

        <Muc tieuDe="Bảng (viền dày ngoài, kẻ mảnh trong) + menu ⋯">
          <Bang>
            <thead>
              <tr>
                <Th>Mẫu ca</Th>
                <Th>Khung giờ</Th>
                <Th>Phòng</Th>
                <Th>Trạng thái</Th>
                <Th className="text-right">Hoàn thành</Th>
                <Th className="w-12" aria-label="Thao tác" />
              </tr>
            </thead>
            <tbody>
              {[
                ["Ca sáng", "07:00 - 15:00", "Phòng Kỹ thuật", true, "92%"],
                ["Ca chiều", "15:00 - 23:00", "Phòng Kỹ thuật", true, "0%"],
                ["Ca hành chính", "08:00 - 17:00", "Phòng Kinh doanh", false, DAU_GACH],
              ].map(([ten, gio, phong, dung, pt]) => (
                <Tr key={ten as string}>
                  <Td className="font-semibold">{ten}</Td>
                  <Td className="tabular-nums">{gio}</Td>
                  <Td>{phong}</Td>
                  <Td>
                    <HuyHieu tong={dung ? "ok" : "trung"}>{dung ? "Đang dùng" : "Đã ngừng"}</HuyHieu>
                  </Td>
                  <Td className="text-right tabular-nums">{pt}</Td>
                  <Td className="text-right">
                    <MenuHanhDong
                      nhan={`Thao tác với ${ten}`}
                      muc={[
                        { nhan: "Sửa", icon: Pencil, onChon: () => {} },
                        { nhan: "Ngừng dùng", icon: Ban, nguyHiem: true, onChon: () => setHop("xacNhan") },
                      ]}
                    />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Bang>
          <The>
            <ThanhPhanTrang offset={offset} limit={20} total={57} doiOffset={setOffset} />
          </The>
        </Muc>

        <Muc tieuDe="Hộp thoại (Radix: bẫy focus, Esc, trả focus)">
          <div className="flex flex-wrap gap-3">
            <Nut bienThe="phu" onClick={() => setHop("thuong")}>
              Mở hộp thường
            </Nut>
            <Nut bienThe="phu" onClick={() => setHop("khongDong")}>
              Mở hộp không đóng tuỳ tiện
            </Nut>
            <Nut bienThe="nguyHiem" onClick={() => setHop("xacNhan")}>
              Mở hộp xác nhận
            </Nut>
          </div>
        </Muc>

        <Muc tieuDe="Thẻ và ba trạng thái dữ liệu">
          <div className="grid grid-cols-3 gap-6">
            <The>
              <TheDau tieuDe="Đang tải" moTa="Khung xương theo hình dạng hàng thật." />
              <TrangThaiTai dong={3} />
            </The>
            <The>
              <TheDau tieuDe="Rỗng" />
              <TrangThaiRong
                icon={Inbox}
                tieuDe="Chưa có từ khoá nào"
                moTa="Thêm từ khoá để AI biết hội thoại nào thuộc phòng này."
                hanhDong={
                  <Nut bienThe="chinh" co="sm" icon={Plus}>
                    Thêm từ khoá
                  </Nut>
                }
              />
            </The>
            <The>
              <TheDau tieuDe="Lỗi" />
              <TrangThaiLoi thongDiep="Không tải được báo cáo. Máy chủ không phản hồi." onThuLai={() => {}} />
            </The>
          </div>
        </Muc>
      </main>

      {hop === "thuong" && (
        <HopThoai
          tieuDe="Thêm từ khoá"
          moTa="Hệ thống bỏ dấu và không phân biệt hoa thường."
          onDong={() => setHop(null)}
          chanDuoi={
            <>
              <NutPhu onClick={() => setHop(null)}>Huỷ</NutPhu>
              <NutChinh onClick={() => setHop(null)}>Lưu</NutChinh>
            </>
          }
        >
          <div className="mt-4">
            <Truong nhan="Từ khoá">{(o) => <ONhap {...o} placeholder="Ví dụ: bảo hành" />}</Truong>
          </div>
        </HopThoai>
      )}
      {hop === "khongDong" && (
        <HopThoai
          tieuDe="Mật khẩu tạm của Trần Quốc Việt"
          moTa="Chép lại ngay: đóng hộp này là không xem lại được nữa. Esc và bấm nền đều bị chặn."
          onDong={null}
          chanDuoi={<NutChinh onClick={() => setHop(null)}>Tôi đã chép, đóng lại</NutChinh>}
        >
          <p className="mt-4 rounded-nb border-2 border-ink bg-sunken px-3 py-2 font-mono text-base font-bold text-ink">
            Tam-Viet-2026-x7
          </p>
        </HopThoai>
      )}
      {hop === "xacNhan" && (
        <HopXacNhan
          tieuDe="Ngừng dùng ca sáng?"
          moTa="Ca đã phân vẫn giữ nguyên, chỉ không phân ca mới được nữa."
          nhanXacNhan="Ngừng dùng"
          nguyHiem
          dangChay={false}
          loi={null}
          onDong={() => setHop(null)}
          onXacNhan={() => setHop(null)}
        />
      )}
    </div>
  );
}
