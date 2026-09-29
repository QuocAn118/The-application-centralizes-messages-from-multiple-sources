/**
 * Logic thuần của Đăng nhập (L1) và Đổi mật khẩu (L2) — tách khỏi màn để test.
 */

/** Chiều dài tối thiểu — khớp `DO_DAI_MAT_KHAU_TOI_THIEU` ở backend (change_password.py). */
export const DO_DAI_MAT_KHAU_TOI_THIEU = 8;

export const LOI_SAI_THONG_TIN = "Sai email hoặc mật khẩu.";

/**
 * Thông điệp lỗi đăng nhập.
 *
 * **Sai email và sai mật khẩu là MỘT câu** (backend cũng trả chung
 * `INVALID_CREDENTIALS`): nói "email không tồn tại" là giúp người ngoài dò danh
 * sách tài khoản. Email sai định dạng (422) cũng gộp vào câu này.
 *
 * Giữ nguyên thông điệp server cho hai trường hợp không lộ gì:
 * - 429 thử quá nhiều lần — người dùng cần biết để chờ, không phải gõ lại;
 * - `INACTIVE_ACCOUNT` — backend chỉ trả SAU KHI mật khẩu đúng, nên người không
 *   có mật khẩu không dùng nó để dò được.
 *
 * `status = null`: không tới được máy chủ (fetch ném lỗi mạng).
 */
export function thongDiepDangNhap(status: number | null, code?: string, message?: string): string {
  if (status === null) return "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.";
  if ((status === 429 || code === "INACTIVE_ACCOUNT") && message) return message;
  if (status >= 500) return "Máy chủ đang gặp sự cố. Thử lại sau ít phút.";
  return LOI_SAI_THONG_TIN;
}

export interface DieuKien {
  nhan: string;
  dat: boolean;
}

/**
 * Điều kiện mật khẩu mới — đúng quy tắc `kiem_tra_do_manh` của backend: ≥ 8 ký
 * tự, có chữ cái (Python `isalpha` = mọi chữ Unicode, nên "đ" cũng tính), có chữ
 * số. Thêm "khớp ô nhập lại" (chỉ FE kiểm, backend không nhận ô đó).
 */
export function dieuKienMatKhau(matKhau: string, nhapLai: string): DieuKien[] {
  return [
    { nhan: `Ít nhất ${DO_DAI_MAT_KHAU_TOI_THIEU} ký tự`, dat: [...matKhau].length >= DO_DAI_MAT_KHAU_TOI_THIEU },
    { nhan: "Có ít nhất một chữ cái", dat: /\p{L}/u.test(matKhau) },
    { nhan: "Có ít nhất một chữ số", dat: /\p{Nd}/u.test(matKhau) },
    { nhan: "Hai ô mật khẩu mới khớp nhau", dat: matKhau.length > 0 && matKhau === nhapLai },
  ];
}

// ---- Nhớ email lần trước ------------------------------------------------------
// CHỈ email, không bao giờ mật khẩu. localStorage có thể ném (chế độ riêng tư,
// chặn dữ liệu trang) — khi đó coi như không nhớ, không làm hỏng đăng nhập.

const KHOA_EMAIL = "omnichat:email-lan-truoc";

export function docEmailDaNho(): string {
  try {
    return localStorage.getItem(KHOA_EMAIL) ?? "";
  } catch {
    return "";
  }
}

export function ghiEmailDaNho(email: string | null): void {
  try {
    if (email) localStorage.setItem(KHOA_EMAIL, email);
    else localStorage.removeItem(KHOA_EMAIL);
  } catch {
    // bỏ qua — xem chú thích trên
  }
}
