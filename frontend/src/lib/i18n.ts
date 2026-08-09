/**
 * Chuỗi hiển thị, gom một chỗ (nợ (d) — spec §9).
 *
 * Bản đầu chỉ có tiếng Việt. Mục đích của lớp này KHÔNG phải dịch ngay, mà là
 * để thêm ngôn ngữ sau chỉ còn là thêm một từ điển — thay vì lùng chuỗi rải
 * rác trong hàng chục component.
 *
 * Cố ý không dùng thư viện i18n: ứng dụng nội bộ một ngôn ngữ, thêm phụ thuộc
 * và đổi cấu trúc route là cái giá không đáng ở thời điểm này.
 *
 * Cách thêm tiếng Anh sau này:
 * 1. Tạo `const EN: TuDien = {...}` cùng khoá.
 * 2. Đổi `TU_DIEN_HIEN_TAI` theo lựa chọn người dùng (hoặc `navigator.language`).
 * 3. Không component nào phải sửa.
 */

const VI = {
  // Chung
  "chung.dangTai": "Đang tải…",
  "chung.thuLai": "Thử lại",
  "chung.huy": "Huỷ",
  "chung.dong": "Đóng",
  "chung.loiKetNoi": "Không kết nối được máy chủ.",

  // Đăng nhập
  "dangNhap.tieuDe": "OmniChat",
  "dangNhap.phuDe": "Hộp thư đa kênh — Zalo, Facebook, Instagram",
  "dangNhap.email": "Email",
  "dangNhap.matKhau": "Mật khẩu",
  "dangNhap.nut": "Đăng nhập",
  "dangNhap.dangGui": "Đang đăng nhập…",
  "dangNhap.loiChung": "Email hoặc mật khẩu không đúng.",
  "dangNhap.hienMatKhau": "Hiện mật khẩu",
  "dangNhap.anMatKhau": "Ẩn mật khẩu",

  // Điều hướng
  "nav.hopThu": "Hộp thư",
  "nav.nhanSu": "Nhân sự",
  "nav.baoCao": "Báo cáo",
  "nav.cauHinh": "Cấu hình",
  "nav.dangXuat": "Đăng xuất",
  "nav.sauNay": "Sẽ có ở phiên bản sau",

  // Danh sách inbox
  "inbox.tieuDe": "Hộp thư",
  "inbox.timKiem": "Tìm theo tên khách…",
  "inbox.timKiemNhan": "Tìm theo tên khách",
  "inbox.xoaTimKiem": "Xoá tìm kiếm",
  "inbox.locTatCa": "Tất cả",
  "inbox.dangCapNhat": "Đang cập nhật…",
  "inbox.trangTruoc": "Trang trước",
  "inbox.trangSau": "Trang sau",
  "inbox.khongCoHoiThoai": "Chưa có hội thoại",
  "inbox.khongTimThay": "Không tìm thấy",
  "inbox.goiYKhiRong": "Khi khách nhắn tới, hội thoại sẽ hiện ở đây.",
  "inbox.loiTai": "Không tải được danh sách",
  "inbox.chonHoiThoai": "Chọn một hội thoại để bắt đầu",
  "inbox.chonHoiThoaiPhu": "Danh sách hội thoại ở cột bên trái.",
  "inbox.khachChuaRoTen": "Khách chưa rõ tên",

  // Khung chat
  "chat.dangTaiHoiThoai": "Đang tải hội thoại…",
  "chat.loiTai": "Không tải được hội thoại",
  "chat.khongCoQuyen": "Không xem được hội thoại này",
  "chat.chuaCoTin": "Chưa có tin nhắn nào trong hội thoại này.",
  "chat.xemTinCu": "Xem tin cũ hơn",
  "chat.daPhanPhong": "Đã phân phòng",
  "chat.chuaPhanPhong": "Chưa phân phòng",
  "chat.dangXuLy": "Đang được xử lý",
  "chat.chuaCoNguoiXuLy": "Chưa có người xử lý",
  "chat.tinKhongCoNoiDung": "(tin không có nội dung)",
  "chat.anhDinhKem": "Ảnh đính kèm",
  "chat.tepDinhKem": "[tệp đính kèm]",
  "chat.loiTaiTep": "[không tải được tệp — thử mở lại hội thoại]",

  // Ô soạn tin
  "soan.nhapNoiDung": "Nhập nội dung trả lời…",
  "soan.nhan": "Nội dung trả lời",
  "soan.gui": "Gửi",
  "soan.dangGui": "Đang gửi…",
  "soan.khongTheNhap": "Không thể nhập",
  "soan.dinhKemAnh": "Đính kèm ảnh",
  "soan.chiGuiAnh": "Chỉ gửi được tệp ảnh.",
  "soan.khoaChoPhan":
    "Hội thoại chưa được phân phòng — hãy phân phòng hoặc nhận việc để trả lời.",
  "soan.khoaDaDong": "Hội thoại đã đóng — không thể gửi tin mới.",
  "soan.loiGuiChung": "Không gửi được tin. Kiểm tra kết nối rồi thử lại.",

  // Hành động
  "hanhDong.nhanViec": "Nhận việc",
  "hanhDong.dangNhan": "Đang nhận…",
  "hanhDong.dong": "Đóng hội thoại",
  "hanhDong.dangDong": "Đang đóng…",
  "hanhDong.phanPhong": "Phân phòng",
  "hanhDong.dangPhan": "Đang phân…",
  "hanhDong.loiChung": "Không thực hiện được. Kiểm tra kết nối rồi thử lại.",

  // Dialog phân phòng
  "phanPhong.tieuDe": "Phân phòng ban",
  "phanPhong.phongBan": "Phòng ban",
  "phanPhong.dangTai": "Đang tải phòng ban…",
  "phanPhong.loiTai": "Không tải được danh sách phòng ban.",
  "phanPhong.khongCoPhong": "Bạn chưa thuộc phòng ban nào nên không thể phân hội thoại.",

  // Trạng thái & vai
  "trangThai.CHO_PHAN": "Chờ phân",
  "trangThai.DANG_MO": "Đang mở",
  "trangThai.DA_DONG": "Đã đóng",
  "kenh.ZALO": "Zalo",
  "kenh.FACEBOOK": "Facebook",
  "kenh.INSTAGRAM": "Instagram",
  "vai.STAFF": "Nhân viên",
  "vai.MANAGER": "Quản lý",
  "vai.ADMIN": "Quản trị",

  // Đổi mật khẩu
  "doiMatKhau.tieuDe": "Đổi mật khẩu",
  "doiMatKhau.batBuoc": "Bạn đang dùng mật khẩu tạm. Hãy đặt mật khẩu mới để tiếp tục.",
  "doiMatKhau.tuNguyen": "Đặt mật khẩu mới cho tài khoản của bạn.",
  "doiMatKhau.hienTai": "Mật khẩu hiện tại",
  "doiMatKhau.moi": "Mật khẩu mới",
  "doiMatKhau.nhapLai": "Nhập lại mật khẩu mới",
  "doiMatKhau.goiYDoDai": "Ít nhất 8 ký tự",
  "doiMatKhau.nut": "Đổi mật khẩu",
  "doiMatKhau.dangLuu": "Đang lưu…",
  "doiMatKhau.khongKhop": "Hai ô mật khẩu mới không khớp.",
  "doiMatKhau.quaNgan": "Mật khẩu mới phải có ít nhất 8 ký tự.",
  "doiMatKhau.loiChung": "Không đổi được mật khẩu.",
} as const;

export type KhoaChuoi = keyof typeof VI;
export type TuDien = Record<KhoaChuoi, string>;

const TU_DIEN_HIEN_TAI: TuDien = VI;

/**
 * Lấy chuỗi hiển thị theo khoá.
 *
 * ``bien`` thay các chỗ giữ dạng ``{ten}``. Khoá được TypeScript kiểm nên gõ
 * sai tên là lỗi biên dịch, không phải chuỗi lạ hiện ra giữa giao diện.
 */
export function t(khoa: KhoaChuoi, bien?: Record<string, string | number>): string {
  const chuoi = TU_DIEN_HIEN_TAI[khoa];
  if (!bien) return chuoi;
  return chuoi.replace(/\{(\w+)\}/g, (nguyen, ten: string) =>
    ten in bien ? String(bien[ten]) : nguyen,
  );
}
