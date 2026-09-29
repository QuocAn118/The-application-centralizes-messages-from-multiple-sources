/**
 * Khung chia đôi của Đăng nhập + Đổi mật khẩu (redesign Phần 6, L1/L2).
 *
 * Trái: khối vàng, tiêu đề lớn và 4 thẻ tin nhắn mẫu từ 4 kênh (logo thật qua
 * `IconKenh`) xếp lệch — nói bằng hình ảnh app làm gì. Không ảnh nền, không
 * animation: chỉ viền + bóng cứng tĩnh.
 * Phải: nền giấy, `children` là form trong `The`.
 *
 * Cột trái là minh hoạ nên `aria-hidden` toàn bộ trừ tiêu đề; trình đọc màn hình
 * đọc tiêu đề rồi vào thẳng form.
 */

import { IconKenh } from "@/components/ui/icon-kenh";
import { Logo } from "@/components/ui/logo";
import type { Platform } from "@/lib/types";

const TIN_MAU: { kenh: Platform; ten: string; noiDung: string; luc: string; lop: string }[] = [
  {
    kenh: "TELEGRAM",
    ten: "Chị Hạnh",
    noiDung: "Shop ơi, đơn #2481 của mình giao chưa ạ? Thứ Bảy mình cần rồi.",
    luc: "vừa xong",
    lop: "ml-0 -rotate-[1.5deg]",
  },
  {
    kenh: "ZALO",
    ten: "Anh Tuấn · Quận 7",
    noiDung: "Máy lọc nước bên em còn bảo hành 12 tháng không em?",
    luc: "2 phút",
    lop: "ml-14 rotate-[1deg]",
  },
  {
    kenh: "INSTAGRAM",
    ten: "minhthu.decor",
    noiDung: "Mẫu đèn trong story hôm qua còn màu trắng không shop?",
    luc: "5 phút",
    lop: "ml-5 -rotate-[0.5deg]",
  },
  {
    kenh: "FACEBOOK",
    ten: "Lê Văn Phúc",
    noiDung: "Cho mình dời lịch lắp đặt sang chiều mai được không?",
    luc: "12 phút",
    lop: "ml-20 rotate-[1.5deg]",
  },
];

export function KhungXacThuc({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] bg-paper">
      <section className="flex flex-col justify-center gap-8 overflow-hidden border-r-[3px] border-ink bg-accent px-14 py-12">
        <p className="flex items-center gap-3 text-2xl font-extrabold tracking-tight text-ink">
          <Logo co={52} />
          OmniChat
        </p>

        <div>
          <h1 className="text-[clamp(52px,5.4vw,88px)] font-black leading-[0.95] tracking-[-0.03em] text-ink">
            Mọi tin nhắn.
            <br />
            Một hộp thư.
          </h1>
          <p className="mt-4 max-w-[44ch] text-base font-semibold text-ink">
            Telegram, Zalo, Instagram, Facebook — gom về một chỗ, tự chia đúng phòng, không để khách
            nào chờ quên.
          </p>
        </div>

        <ul aria-hidden className="flex max-w-[460px] flex-col gap-3">
          {TIN_MAU.map((tin) => (
            <li
              key={tin.kenh}
              className={`rounded-nb border-2 border-ink bg-card px-4 py-3 shadow-nb ${tin.lop}`}
            >
              <div className="flex items-center gap-2">
                <IconKenh kenh={tin.kenh} co={18} />
                <span className="text-sm font-bold text-ink">{tin.ten}</span>
                <span className="ml-auto text-xs font-semibold text-ink-2">{tin.luc}</span>
              </div>
              <p className="mt-1 text-sm leading-snug text-ink">{tin.noiDung}</p>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex items-center justify-center px-10 py-12">{children}</div>
    </main>
  );
}
