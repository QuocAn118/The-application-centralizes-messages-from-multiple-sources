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
  "nav.tuKhoa": "Từ khoá",
  "nav.cauHinh": "Cấu hình",
  "nav.dangXuat": "Đăng xuất",
  "nav.sauNay": "Sẽ có ở phiên bản sau",
  "nav.khongDuQuyen": "Bạn không có quyền vào mục này",

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
  "kenh.TELEGRAM": "Telegram",
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

  // Quản trị (#F2) — chung
  "quanTri.tieuDe": "Quản trị",
  "quanTri.tabNguoiDung": "Người dùng",
  "quanTri.tabPhongBan": "Phòng ban",
  "quanTri.tabKenh": "Kênh",
  "quanTri.tabNhatKy": "Nhật ký",
  "quanTri.khongCoQuyen": "Bạn không có quyền vào khu vực này.",
  "quanTri.trong": "Không có dữ liệu.",
  "quanTri.truoc": "Trước",
  "quanTri.sau": "Sau",
  "quanTri.hienThi": "Hiển thị {tu}–{den} trong {tong}",
  "quanTri.tatCa": "Tất cả",
  "quanTri.veHopThu": "Về hộp thư",

  // Quản trị — người dùng
  "nguoiDung.tieuDe": "Người dùng",
  "nguoiDung.taoMoi": "Tạo tài khoản",
  "nguoiDung.timKiem": "Tìm theo tên hoặc email",
  "nguoiDung.locVaiTro": "Vai trò",
  "nguoiDung.locPhongBan": "Phòng ban",
  "nguoiDung.locTrangThai": "Trạng thái",
  "nguoiDung.dangHoatDong": "Đang hoạt động",
  "nguoiDung.daVoHieuHoa": "Đã vô hiệu hoá",
  "nguoiDung.cotNguoiDung": "Người dùng",
  "nguoiDung.cotVaiTro": "Vai trò",
  "nguoiDung.cotPhongBan": "Phòng ban",
  "nguoiDung.cotTrangThai": "Trạng thái",
  "nguoiDung.khongPhong": "—",
  "nguoiDung.thaoTac": "Thao tác",
  "nguoiDung.suaHoSo": "Sửa hồ sơ",
  "nguoiDung.doiVaiTro": "Đổi vai trò",
  "nguoiDung.doiPhongBan": "Đổi phòng ban",
  "nguoiDung.datLaiMatKhau": "Đặt lại mật khẩu",
  "nguoiDung.voHieuHoa": "Vô hiệu hoá",
  "nguoiDung.kichHoatLai": "Kích hoạt lại",
  "nguoiDung.hoTen": "Họ và tên",
  "nguoiDung.email": "Email",
  "nguoiDung.dienThoai": "Số điện thoại",
  "nguoiDung.khongBatBuoc": "(không bắt buộc)",
  "nguoiDung.matKhauTam": "Mật khẩu tạm",
  "nguoiDung.toiThieu8": "Tối thiểu 8 ký tự",
  "nguoiDung.phaiDoiLanDau": "Tài khoản mới sẽ phải đổi mật khẩu ở lần đăng nhập đầu tiên.",
  "nguoiDung.daTao": "Đã tạo tài khoản",
  "nguoiDung.canhBaoMotLan":
    "Mật khẩu tạm chỉ hiện MỘT LẦN. Hãy sao chép và gửi cho người dùng ngay bây giờ.",
  "nguoiDung.saoChep": "Sao chép",
  "nguoiDung.daSaoChep": "Đã sao chép",
  "nguoiDung.dongLai": "Đã sao chép, đóng lại",
  "nguoiDung.xacNhanVoHieu":
    "Vô hiệu hoá {ten}? Người này sẽ bị đăng xuất khỏi mọi thiết bị và không đăng nhập lại được.",
  "nguoiDung.xacNhanKichHoat": "Kích hoạt lại {ten}?",
  "nguoiDung.luu": "Lưu",
  "nguoiDung.chinhBan": "(bạn)",
  "nguoiDung.an": "Ẩn",
  "nguoiDung.hien": "Hiện",
  "nguoiDung.matKhauMoi": "Mật khẩu mới",
  "nguoiDung.canhBaoDatLai": "Người này sẽ bị đăng xuất và phải đổi mật khẩu ở lần đăng nhập kế tiếp.",
  "nguoiDung.daDatLai": "Đã đặt lại mật khẩu",
  "nguoiDung.vaiMoi": "Vai trò mới",
  "nguoiDung.khongDoiSangQuanTri": "Chỉ đổi qua lại giữa Nhân viên và Quản lý.",
  "nguoiDung.phongMoi": "Phòng ban mới",
  "nguoiDung.loiTai": "Không tải được danh sách người dùng.",
  "nguoiDung.moThaoTac": "Mở menu thao tác",

  // Quản trị — phòng ban
  "phongBan.daNgung": "đã ngừng",
  "phongBan.tieuDe": "Phòng ban",
  "phongBan.taoMoi": "Tạo phòng ban",
  "phongBan.timKiem": "Tìm theo tên phòng ban",
  "phongBan.cotTen": "Phòng ban",
  "phongBan.cotSoNhanVien": "Nhân viên",
  "phongBan.cotTrangThai": "Trạng thái",
  "phongBan.dangHoatDong": "Đang hoạt động",
  "phongBan.khongMoTa": "—",
  "phongBan.ten": "Tên phòng ban",
  "phongBan.moTa": "Mô tả",
  "phongBan.sua": "Sửa",
  "phongBan.ngungHoatDong": "Ngừng hoạt động",
  "phongBan.loiTai": "Không tải được danh sách phòng ban.",
  "phongBan.dangDemNhanVien": "đang đếm…",
  "phongBan.conNhanVien":
    "Phòng này còn {so} nhân viên đang hoạt động. Hãy chuyển họ sang phòng khác hoặc vô hiệu hoá họ trước.",
  // Nói rõ KHÔNG hoàn tác được: backend không có endpoint kích hoạt lại phòng
  // ban (khác với người dùng — người dùng có `reactivate`). Nếu chỉ nói "dữ
  // liệu vẫn còn" thì người dùng sẽ tưởng bật lại được.
  "phongBan.xacNhanNgung":
    "Ngừng hoạt động phòng {ten}? Hội thoại và nhật ký cũ vẫn giữ nguyên, nhưng phòng sẽ không nhận việc mới và KHÔNG BẬT LẠI ĐƯỢC.",

  "nguoiDung.dangLuu": "Đang lưu…",

  // Quản trị — kênh
  "kenh.tieuDe": "Kênh",
  "kenh.ketNoi": "Kết nối kênh",
  "kenh.cotKenh": "Kênh",
  "kenh.cotNenTang": "Nền tảng",
  "kenh.cotPhongBan": "Phòng phụ trách",
  "kenh.cotTrangThai": "Trạng thái",
  "kenh.dangKetNoi": "Đang kết nối",
  "kenh.daNgat": "Đã ngắt",
  "kenh.ten": "Tên kênh",
  "kenh.nenTang": "Nền tảng",
  "kenh.maKenh": "Mã kênh trên nền tảng",
  "kenh.maKenhGoiY": "OA ID, Page ID, hoặc chat ID của bot",
  "kenh.phongPhuTrach": "Phòng phụ trách",
  "kenh.khongPhong": "Không gắn phòng",
  // Nhãn NÚT trong bảng: cột hẹp nên để ngắn.
  "kenh.sua": "Sửa",
  // Tiêu đề HỘP THOẠI: "Sửa" trơ trọi trên đầu hộp thì không rõ đang sửa gì.
  "kenh.suaTieuDe": "Sửa kênh",
  "kenh.ngat": "Ngắt kênh",
  "kenh.loiTai": "Không tải được danh sách kênh.",
  "kenh.timKiem": "Tìm theo tên kênh",
  // Nói "token/bí mật" chứ không nói "mật khẩu": đây là token của nền tảng
  // (Zalo OA, Meta, bot Telegram), không phải mật khẩu tài khoản OmniChat.
  "kenh.token": "Token kết nối",
  "kenh.tokenGoiY": "Token do nền tảng cấp (Zalo OA / Meta / bot Telegram)",
  "kenh.tokenGiuNguyen": "Để trống = giữ token hiện tại",
  // Nói cả hai ý trong MỘT dòng ghi chú, không dựa vào placeholder: placeholder
  // biến mất ngay khi người dùng gõ ký tự đầu, đúng lúc họ cần biết nhất.
  "kenh.tokenKhongDocLai":
    "Để trống = giữ token hiện tại. Vì lý do bảo mật, token đã lưu không đọc lại được; muốn đổi thì nhập token mới.",
  "kenh.xacNhanNgat":
    "Ngắt kênh {ten}? Hội thoại và tin nhắn cũ vẫn xem được, nhưng kênh sẽ không nhận tin mới và KHÔNG KẾT NỐI LẠI ĐƯỢC từ màn này.",

  // Quản trị — nhật ký
  "nhatKy.tieuDe": "Nhật ký",
  "nhatKy.cotThoiGian": "Thời gian",
  "nhatKy.cotHanhDong": "Hành động",
  "nhatKy.cotNguoiThucHien": "Người thực hiện",
  "nhatKy.cotDoiTuong": "Đối tượng",
  "nhatKy.locHanhDong": "Hành động",
  "nhatKy.locLoaiDoiTuong": "Loại đối tượng",
  "nhatKy.locTuNgay": "Từ ngày",
  "nhatKy.locDenNgay": "Đến ngày",
  "nhatKy.heThong": "Hệ thống",
  "nhatKy.khongRo": "Không rõ",
  "nhatKy.xoaLoc": "Xoá bộ lọc",
  "nhatKy.chiDoc": "Nhật ký chỉ để tra cứu, không sửa hay xoá được.",
  "nhatKy.loaiUser": "Người dùng",
  "nhatKy.loaiDepartment": "Phòng ban",
  "nhatKy.loaiAuth": "Xác thực",

  // Nhãn 15 giá trị AuditAction. Nhóm theo tiền tố `user.` / `department.` /
  // `auth.` đúng như backend đặt tên (RB-9: bảng tra phải phủ ĐỦ, có test duyệt
  // toàn bộ enum — bài học TELEGRAM).
  "hanhDong.user.created": "Tạo tài khoản",
  "hanhDong.user.updated": "Sửa hồ sơ",
  "hanhDong.user.deactivated": "Vô hiệu hoá tài khoản",
  "hanhDong.user.reactivated": "Kích hoạt lại tài khoản",
  "hanhDong.user.role_changed": "Đổi vai trò",
  "hanhDong.user.department_changed": "Đổi phòng ban",
  "hanhDong.user.password_reset": "Đặt lại mật khẩu",
  "hanhDong.user.password_changed": "Tự đổi mật khẩu",
  "hanhDong.department.created": "Tạo phòng ban",
  "hanhDong.department.updated": "Sửa phòng ban",
  "hanhDong.department.deactivated": "Ngừng hoạt động phòng ban",
  "hanhDong.auth.login_succeeded": "Đăng nhập thành công",
  "hanhDong.auth.login_failed": "Đăng nhập thất bại",
  "hanhDong.auth.logout": "Đăng xuất",
  // Không dịch thành câu kỹ thuật: đây là dấu hiệu token bị dùng lại sau khi
  // đã xoay — thường là bị đánh cắp. Người đọc nhật ký cần thấy ngay mức độ.
  "hanhDong.auth.token_reuse_detected": "Phát hiện token bị dùng lại (nghi ngờ đánh cắp)",

  // Nhân sự (#F3) — chung
  "nhanSu.tieuDe": "Nhân sự",
  "nhanSu.tabCa": "Ca làm việc",
  "nhanSu.tabDon": "Đơn từ",
  "nhanSu.tabKpi": "KPI",

  // Nhân sự — đơn từ
  "don.tieuDe": "Đơn từ",
  "don.guiDon": "Gửi đơn",
  "don.cotNguoiGui": "Người gửi",
  "don.cotLoaiDon": "Loại đơn",
  "don.cotNoiDung": "Nội dung",
  "don.cotTrangThai": "Trạng thái",
  "don.cotNgayGui": "Ngày gửi",
  "don.locTrangThai": "Trạng thái",
  "don.loaiDon": "Loại đơn",
  "don.lyDo": "Lý do",
  "don.tuNgay": "Từ ngày",
  "don.denNgay": "Đến ngày",
  "don.duyet": "Duyệt",
  "don.tuChoi": "Từ chối",
  "don.thuHoi": "Thu hồi",
  "don.lyDoTuChoi": "Lý do từ chối",
  "don.batBuocLyDoTuChoi": "Từ chối bắt buộc phải nêu lý do.",
  "don.xacNhanDuyet": "Duyệt đơn {loai} của {ten}? Quyết định này không sửa lại được.",
  "don.xacNhanThuHoi": "Thu hồi đơn này? Đơn đã thu hồi không gửi lại được, phải tạo đơn mới.",
  "don.chinhBan": "(bạn)",
  "don.loiTai": "Không tải được danh sách đơn.",
  "don.khoangNghi": "{tu} → {den}",
  "don.adminKhongGuiDuoc":
    "Quản trị viên không thuộc phòng ban nào nên không gửi được đơn từ.",
  "don.daQuyetDinh": "{nguoi} · {luc}",

  // Nhãn RequestType (3 giá trị) — RB-9: bảng tra phải phủ đủ.
  "loaiDon.NGHI_PHEP": "Nghỉ phép",
  "loaiDon.TANG_LUONG": "Tăng lương",
  "loaiDon.KHAC": "Khác",

  // Nhãn RequestStatus (4 giá trị).
  "trangThaiDon.CHO_DUYET": "Chờ duyệt",
  "trangThaiDon.DA_DUYET": "Đã duyệt",
  "trangThaiDon.TU_CHOI": "Từ chối",
  "trangThaiDon.DA_HUY": "Đã thu hồi",

  // Nhân sự — ca làm việc
  "ca.tieuDe": "Mẫu ca",
  "ca.taoMoi": "Tạo mẫu ca",
  "ca.sua": "Sửa",
  "ca.suaTieuDe": "Sửa mẫu ca",
  "ca.ngung": "Ngừng dùng",
  "ca.ten": "Tên ca",
  "ca.batDau": "Giờ bắt đầu",
  "ca.ketThuc": "Giờ kết thúc",
  "ca.phongBan": "Phòng ban",
  // Backend KHONG cho ca qua nua dem ("ca khong qua nua dem o #4" —
  // shift.py), tra 422 INVALID_SHIFT_WINDOW. Chan truoc va noi ro ly do.
  "ca.gioKetThucPhaiSau":
    "Giờ kết thúc phải sau giờ bắt đầu — hệ thống chưa hỗ trợ ca qua đêm.",
  "ca.dangDung": "Đang dùng",
  "ca.daNgung": "Đã ngừng",
  "ca.loiTai": "Không tải được mẫu ca.",
  "ca.chuaCoCa": "Chưa có mẫu ca nào. Tạo mẫu ca trước khi xếp lịch.",
  "ca.xacNhanNgung":
    "Ngừng dùng mẫu ca {ten}? Các buổi đã xếp vẫn giữ nguyên, nhưng không xếp thêm được nữa và KHÔNG BẬT LẠI ĐƯỢC.",

  // Nhân sự — lịch phân ca
  "lich.tieuDe": "Lịch phân ca",
  "lich.tuanTruoc": "Tuần trước",
  "lich.tuanSau": "Tuần sau",
  "lich.tuanNay": "Tuần này",
  "lich.cotNhanVien": "Nhân viên",
  "lich.phanCa": "Xếp ca",
  "lich.huyPhanCa": "Huỷ ca",
  "lich.chonCa": "Mẫu ca",
  "lich.chonNhanVien": "Nhân viên",
  "lich.ngayLam": "Ngày làm",
  "lich.loiTai": "Không tải được lịch phân ca.",
  "lich.khongCoNhanVien": "Phòng này chưa có nhân viên đang hoạt động.",
  "lich.xacNhanHuy": "Huỷ buổi ca {ca} ngày {ngay} của {ten}?",
  "lich.trong": "Chưa xếp ca nào trong tuần này.",
  "lich.themVaoO": "Xếp ca ngày {ngay}",

  // KPI (#F3 GĐ3)
  "kpi.tieuDe": "Mục tiêu KPI",
  "kpi.datMucTieu": "Đặt mục tiêu",
  "kpi.suaMucTieu": "Sửa mục tiêu",
  "kpi.ky": "Tháng {thang}/{nam}",
  "kpi.chonKy": "Kỳ",
  "kpi.chonThang": "Tháng",
  "kpi.chonNam": "Năm",
  "kpi.cotDoiTuong": "Đối tượng",
  "kpi.cotChiSo": "Chỉ số",
  "kpi.cotMucTieu": "Mục tiêu",
  "kpi.cotThucDat": "Thực đạt",
  "kpi.cotHoanThanh": "Hoàn thành",
  "kpi.chiSo": "Chỉ số",
  "kpi.loaiDoiTuong": "Áp cho",
  "kpi.doiTuongUser": "Nhân viên",
  "kpi.doiTuongPhong": "Cả phòng",
  "kpi.chonNhanVien": "Nhân viên",
  "kpi.chonPhong": "Phòng ban",
  "kpi.giaTriMucTieu": "Giá trị mục tiêu",
  "kpi.CONVERSATIONS_CLOSED": "Hội thoại đã đóng",
  "kpi.AVG_RESPONSE_MINUTES": "Phút phản hồi trung bình",
  "kpi.donViHoiThoai": "hội thoại",
  "kpi.donViPhut": "phút",
  "kpi.chuaCoMucTieu": "Chưa có mục tiêu KPI nào trong kỳ này.",
  "kpi.loiTai": "Không tải được mục tiêu KPI.",
  "kpi.dangTinh": "Đang tính…",
  // Nói rõ vì sao ô trống, nếu không người dùng sẽ đọc dấu gạch thành số 0.
  "kpi.chuaCoSoLieu": "Chưa có số liệu trong kỳ này",
  "kpi.ghiChuThucDat":
    "Giá trị thực đạt và phần trăm hoàn thành lấy tự động từ dữ liệu hội thoại, không nhập tay.",
  "kpi.deDatLai": "Đặt lại giá trị cho cùng đối tượng và kỳ sẽ ghi đè mục tiêu cũ.",
  "kpi.khongDatDuoc": "Chỉ quản lý và quản trị viên đặt được mục tiêu KPI.",
  "kpi.giaTriPhaiDuong": "Giá trị mục tiêu không được âm.",
  "kpi.khongCoNhanVien": "Phòng này chưa có nhân viên đang hoạt động.",

  // Quản trị — lỗi
  //
  // Backend ĐÃ trả thông điệp tiếng Việt đầy đủ cho mọi vi phạm quy tắc nghiệp
  // vụ (xem `identity/domain/entities/user.py`: DEPARTMENT_ALREADY_HAS_MANAGER,
  // LAST_ADMIN_CANNOT_BE_DEACTIVATED, INACTIVE_DEPARTMENT, CANNOT_CHANGE_TO_ADMIN…).
  // Nên UI HIỆN THẲNG message của server thay vì dịch lại mã lỗi ở đây — hai
  // bản thông điệp song song chắc chắn sẽ lệch nhau khi backend đổi.
  //
  // Chỉ giữ ở đây các trường hợp server KHÔNG nói được: lỗi mạng, và mã lỗi lạ.
  // Từ khoá & Phân tích AI (#F4)
  "quanTri.tabTuKhoa": "Từ khoá",
  "quanTri.tabPhanTich": "Phân tích AI",

  "tuKhoa.tieuDeKhu": "Từ khoá & AI",
  "tuKhoa.tieuDe": "Từ khoá theo phòng",
  "tuKhoa.them": "Thêm từ khoá",
  "tuKhoa.suaTieuDe": "Sửa từ khoá",
  "tuKhoa.noiDung": "Từ khoá",
  "tuKhoa.phongBan": "Phòng ban",
  "tuKhoa.sua": "Sửa",
  "tuKhoa.xoa": "Xoá",
  "tuKhoa.chuaCo": "Chưa có từ khoá nào. Thêm từ khoá để AI biết phòng này phụ trách việc gì.",
  // Staff không có nút Thêm — bảo họ "thêm từ khoá" là chỉ vào một nút không
  // tồn tại, cùng loại lỗi với nút chết. Nói ai làm được việc đó.
  "tuKhoa.chuaCoChiXem": "Chưa có từ khoá nào. Quản lý phòng là người thêm từ khoá cho AI.",
  "tuKhoa.chuaCoTrongPhong": "Phòng này chưa có từ khoá nào.",
  "tuKhoa.loiTai": "Không tải được danh sách từ khoá.",
  "tuKhoa.xacNhanXoa": "Xoá từ khoá {ten}? AI sẽ không còn dùng từ này để phân phòng.",
  // Nói cho người dùng biết vì sao "Bảo Hành" bị coi là trùng với "bao hanh".
  "tuKhoa.dangKhop": "dạng khớp: {chuan}",
  "tuKhoa.giaiThichChuanHoa":
    "Hệ thống bỏ dấu và không phân biệt hoa thường, nên \"Bảo Hành\" và \"bao hanh\" là một.",
  "tuKhoa.demTrongPhong": "{so} từ khoá",
  "tuKhoa.timGoiY": "Tìm từ khoá…",

  "phanTich.tieuDe": "Phân tích hội thoại bằng AI",
  "phanTich.cotHoiThoai": "Hội thoại",
  "phanTich.cotKetQua": "Kết quả",
  "phanTich.cotPhongDeXuat": "Phòng đề xuất",
  "phanTich.cotTinCay": "Độ tin cậy",
  "phanTich.cotNhuCau": "Nhu cầu nhận ra",
  "phanTich.cotThoiDiem": "Thời điểm",
  "phanTich.AUTO_ASSIGNED": "Đã tự phân",
  "phanTich.AMBIGUOUS": "Chưa rõ phòng",
  "phanTich.NOT_ANALYZED": "Không phân tích được",
  "phanTich.chuaCo": "Chưa có kết quả phân tích nào.",
  "phanTich.loiTai": "Không tải được kết quả phân tích.",
  "phanTich.khongCoNhuCau": "Không trích được nhu cầu nào",
  "phanTich.chiDoc": "Màn này chỉ để xem. Kết quả do AI tự chạy khi có hội thoại mới.",
  "phanTich.khongRoPhong": "Không xác định được phòng",

  "loiQuanTri.khongDuQuyen": "Bạn không có quyền thực hiện thao tác này.",
  "loiQuanTri.chung": "Không thực hiện được. Hãy thử lại.",
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
