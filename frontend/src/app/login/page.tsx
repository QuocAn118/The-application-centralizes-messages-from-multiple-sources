"use client";

/**
 * Màn đăng nhập (redesign Phần 6, L1).
 *
 * Không có "Đăng ký": tài khoản do Admin cấp (module #4). "Quên mật khẩu?" chỉ
 * nói cách xin cấp lại — không có luồng tự đặt lại.
 *
 * Lỗi luôn là một câu chung cho sai email / sai mật khẩu (`thongDiepDangNhap`).
 * Chỉ nhớ EMAIL lần trước (localStorage), không bao giờ nhớ mật khẩu.
 */

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { CircleAlert, Eye, EyeOff, LogIn, TriangleAlert } from "lucide-react";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { docEmailDaNho, ghiEmailDaNho, thongDiepDangNhap } from "@/lib/xac-thuc";
import { KhungXacThuc } from "@/components/khung-xac-thuc";
import { The } from "@/components/ui/the";
import { Truong } from "@/components/ui/truong";
import { ONhap } from "@/components/ui/o-nhap";
import { Nut } from "@/components/ui/nut";
import { NutIcon } from "@/components/ui/nut-icon";

/** localStorage không phát sự kiện trong cùng tab — chỉ cần đọc một lần. */
const khongDoi = () => () => {};

export default function LoginPage() {
  const { login, user, isLoading } = useAuth();
  const router = useRouter();

  // Email nhớ từ lần trước: server không có localStorage nên trả "", client đọc
  // sau hydrate — `useSyncExternalStore` làm đúng việc đó mà không lệch hydrate.
  const emailDaNho = useSyncExternalStore(khongDoi, docEmailDaNho, () => "");
  // `null` = người dùng chưa gõ gì → dùng email đã nhớ.
  const [emailGo, setEmail] = useState<string | null>(null);
  const email = emailGo ?? emailDaNho;
  const [matKhau, setMatKhau] = useState("");
  const [nhoEmail, setNhoEmail] = useState(true);
  const [hienMatKhau, setHienMatKhau] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [moQuenMatKhau, setMoQuenMatKhau] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, setDangGui] = useState(false);
  // Chặn bấm lặp NGAY lập tức: state `dangGui` chỉ có hiệu lực ở lần render sau,
  // hai lần Enter liên tiếp vẫn lọt được giữa hai lần render.
  const dangGuiRef = useRef(false);
  const oMatKhau = useRef<HTMLInputElement>(null);

  // Có email cũ thì đặt con trỏ vào ô mật khẩu — việc duy nhất còn lại.
  useEffect(() => {
    if (emailDaNho) oMatKhau.current?.focus();
  }, [emailDaNho]);

  useEffect(() => {
    if (!isLoading && user) router.replace("/inbox");
  }, [isLoading, user, router]);

  async function xuLyGui(e: React.FormEvent) {
    e.preventDefault();
    if (dangGuiRef.current) return;
    dangGuiRef.current = true;
    setLoi(null);
    setDangGui(true);
    try {
      const me = await login(email.trim(), matKhau);
      ghiEmailDaNho(nhoEmail ? email.trim() : null);
      // Mật khẩu tạm: bắt đổi trước khi vào việc.
      router.replace(me.must_change_password ? "/doi-mat-khau" : "/inbox");
    } catch (err) {
      setLoi(
        err instanceof ApiError
          ? thongDiepDangNhap(err.status, err.code, err.message)
          : thongDiepDangNhap(null),
      );
      setMatKhau("");
      oMatKhau.current?.focus();
      dangGuiRef.current = false;
      setDangGui(false);
    }
  }

  // Caps Lock đọc từ chính phím vừa gõ — trình duyệt không cho hỏi trạng thái
  // khi chưa có sự kiện phím.
  const docCapsLock = (e: React.KeyboardEvent) => setCapsLock(e.getModifierState("CapsLock"));

  return (
    <KhungXacThuc>
      <The className="w-full max-w-[440px] px-8 py-9">
        <h2 className="text-[28px] font-extrabold leading-tight tracking-tight text-ink">Đăng nhập</h2>
        <p className="mt-1 text-sm text-ink-2">Dùng tài khoản quản trị viên đã cấp cho bạn.</p>

        <form onSubmit={xuLyGui} onKeyDown={docCapsLock} onKeyUp={docCapsLock} className="mt-7 flex flex-col gap-5">
          <Truong nhan="Email">
            {(o) => (
              <ONhap
                {...o}
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ten@congty.vn"
                autoFocus
              />
            )}
          </Truong>

          <Truong nhan="Mật khẩu">
            {(o) => (
              <div className="relative">
                <ONhap
                  {...o}
                  ref={oMatKhau}
                  type={hienMatKhau ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  value={matKhau}
                  onChange={(e) => setMatKhau(e.target.value)}
                  className="pr-11"
                />
                <NutIcon
                  icon={hienMatKhau ? EyeOff : Eye}
                  nhan={hienMatKhau ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  co="sm"
                  aria-pressed={hienMatKhau}
                  onClick={() => setHienMatKhau((v) => !v)}
                  className="absolute right-1 top-1"
                />
              </div>
            )}
          </Truong>

          {/* Vùng live luôn có mặt để trình đọc màn hình đọc khi cảnh báo XUẤT HIỆN. */}
          <div aria-live="polite" className="-mt-3 empty:hidden">
            {capsLock && (
              <p className="flex items-center gap-1.5 text-xs font-bold text-wait">
                <TriangleAlert aria-hidden className="size-4" strokeWidth={2.5} />
                Caps Lock đang bật
              </p>
            )}
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-ink">
            <input
              type="checkbox"
              checked={nhoEmail}
              onChange={(e) => setNhoEmail(e.target.checked)}
              className="size-4 accent-ink"
            />
            Nhớ email trên máy này
          </label>

          {loi && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-nb border-2 border-bad bg-bad-bg px-3 py-2.5 text-sm font-semibold text-bad"
            >
              <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" strokeWidth={2.5} />
              {loi}
            </p>
          )}

          <Nut
            type="submit"
            bienThe="chinh"
            icon={LogIn}
            dangChay={dangGui}
            // Không `disabled` khi ô trống: nút chính luôn vàng, ô `required`
            // để trình duyệt tự báo ô nào còn thiếu khi bấm.
            className="h-12 w-full text-base"
          >
            {dangGui ? "Đang đăng nhập…" : "Đăng nhập"}
          </Nut>
        </form>

        <div className="mt-5 border-t-2 border-line pt-4">
          <button
            type="button"
            aria-expanded={moQuenMatKhau}
            aria-controls="goi-y-quen-mat-khau"
            onClick={() => setMoQuenMatKhau((v) => !v)}
            className="text-sm font-bold text-accent-2 underline underline-offset-2 hover:no-underline"
          >
            Quên mật khẩu?
          </button>
          {moQuenMatKhau && (
            <p id="goi-y-quen-mat-khau" className="mt-2 text-sm text-ink">
              Liên hệ quản trị viên để được cấp lại mật khẩu tạm. Lần đăng nhập sau bạn sẽ được yêu cầu
              đặt mật khẩu mới.
            </p>
          )}
        </div>
      </The>
    </KhungXacThuc>
  );
}
