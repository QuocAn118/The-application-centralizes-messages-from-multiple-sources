"use client";

/**
 * Đổi mật khẩu (redesign Phần 6, L2) — bắt buộc với người vừa được Admin cấp
 * mật khẩu tạm (`must_change_password`), hoặc tự nguyện.
 *
 * Không nằm dưới `/inbox` nên không bị `AuthGuard` của nhóm đó bọc; tự kiểm tra
 * phiên ở đây. Backend cố ý cho phép gọi endpoint này kể cả khi chưa đổi mật
 * khẩu — nếu chặn thì người dùng sẽ mắc kẹt.
 *
 * Danh sách điều kiện tick dần khi gõ, quy tắc lấy đúng `kiem_tra_do_manh` của
 * backend (`dieuKienMatKhau`). Nút chỉ bật khi đạt đủ — server vẫn là trọng tài.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, CircleAlert, Circle, KeyRound } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { dieuKienMatKhau } from "@/lib/xac-thuc";
import { KhungXacThuc } from "@/components/khung-xac-thuc";
import { The } from "@/components/ui/the";
import { Truong } from "@/components/ui/truong";
import { ONhap } from "@/components/ui/o-nhap";
import { Nut } from "@/components/ui/nut";

export default function DoiMatKhauPage() {
  const { user, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [matKhauHienTai, setMatKhauHienTai] = useState("");
  const [matKhauMoi, setMatKhauMoi] = useState("");
  const [xacNhan, setXacNhan] = useState("");
  const [loi, setLoi] = useState<string | null>(null);
  const [dangGui, setDangGui] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  const dieuKien = dieuKienMatKhau(matKhauMoi, xacNhan);
  const hopLe = matKhauHienTai.length > 0 && dieuKien.every((d) => d.dat);

  async function xuLyGui(e: React.FormEvent) {
    e.preventDefault();
    if (!hopLe || dangGui) return;
    setLoi(null);
    setDangGui(true);
    try {
      await api.post("/auth/change-password", {
        current_password: matKhauHienTai,
        new_password: matKhauMoi,
      });
      // Đọc lại `/auth/me` để cờ `must_change_password` về false.
      await refreshUser();
      router.replace("/inbox");
    } catch (err) {
      setLoi(err instanceof ApiError ? err.message : "Không đổi được mật khẩu. Thử lại.");
      setDangGui(false);
    }
  }

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <p className="text-sm text-ink-2">Đang tải…</p>
      </div>
    );
  }

  return (
    <KhungXacThuc>
      <The className="w-full max-w-[440px] px-8 py-9">
        <h2 className="text-[28px] font-extrabold leading-tight tracking-tight text-ink">Đổi mật khẩu</h2>
        <p className="mt-1 text-sm text-ink-2">
          {user.must_change_password
            ? "Bạn đang dùng mật khẩu tạm. Đặt mật khẩu mới để tiếp tục."
            : "Đặt mật khẩu mới cho tài khoản của bạn."}
        </p>

        <form onSubmit={xuLyGui} className="mt-7 flex flex-col gap-5">
          <Truong nhan="Mật khẩu hiện tại">
            {(o) => (
              <ONhap
                {...o}
                type="password"
                required
                autoComplete="current-password"
                value={matKhauHienTai}
                onChange={(e) => setMatKhauHienTai(e.target.value)}
                autoFocus
              />
            )}
          </Truong>
          <Truong nhan="Mật khẩu mới">
            {(o) => (
              <ONhap
                {...o}
                aria-describedby="dieu-kien-mat-khau"
                type="password"
                required
                autoComplete="new-password"
                value={matKhauMoi}
                onChange={(e) => setMatKhauMoi(e.target.value)}
              />
            )}
          </Truong>
          <Truong nhan="Nhập lại mật khẩu mới">
            {(o) => (
              <ONhap
                {...o}
                type="password"
                required
                autoComplete="new-password"
                value={xacNhan}
                onChange={(e) => setXacNhan(e.target.value)}
              />
            )}
          </Truong>

          <ul id="dieu-kien-mat-khau" aria-label="Điều kiện mật khẩu" className="flex flex-col gap-1.5">
            {dieuKien.map((d) => (
              <li
                key={d.nhan}
                className={`flex items-center gap-2 text-sm ${d.dat ? "font-bold text-ok" : "text-ink-2"}`}
              >
                <span
                  className={`inline-flex size-5 items-center justify-center rounded-[4px] border-2 ${
                    d.dat ? "border-ok bg-ok-bg" : "border-ink-2"
                  }`}
                >
                  {d.dat ? (
                    <Check aria-hidden className="size-3.5" strokeWidth={3} />
                  ) : (
                    <Circle aria-hidden className="size-2 fill-current" />
                  )}
                </span>
                {d.nhan}
                {/* Không chỉ dựa vào màu + icon: trình đọc màn hình đọc thành chữ. */}
                <span className="sr-only">{d.dat ? "— đã đạt" : "— chưa đạt"}</span>
              </li>
            ))}
          </ul>

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
            icon={KeyRound}
            dangChay={dangGui}
            disabled={!hopLe}
            className="h-12 w-full text-base"
          >
            {dangGui ? "Đang lưu…" : "Đổi mật khẩu"}
          </Nut>
        </form>
      </The>
    </KhungXacThuc>
  );
}
