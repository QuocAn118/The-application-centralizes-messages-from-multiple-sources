/**
 * Đổi một lỗi bất kỳ thành câu hiển thị cho người dùng ở khu quản trị (RB-4).
 *
 * Nguyên tắc: **hiện thẳng `message` của server**. Backend đã viết sẵn thông
 * điệp tiếng Việt đầy đủ cho từng vi phạm quy tắc nghiệp vụ
 * (`DEPARTMENT_ALREADY_HAS_MANAGER`, `LAST_ADMIN_CANNOT_BE_DEACTIVATED`,
 * `INACTIVE_DEPARTMENT`, `CANNOT_CHANGE_TO_ADMIN`,
 * `DEPARTMENT_HAS_ACTIVE_MEMBERS`…). Nếu FE dịch lại các mã này thì có hai bản
 * thông điệp song song, và chúng sẽ lệch nhau ngay lần backend đổi câu chữ.
 *
 * FE chỉ tự viết cho những gì server không nói được: mất mạng, và 403 (nơi
 * server cố ý trả lời mơ hồ để không lộ tài nguyên có tồn tại hay không).
 */

import { ApiError, SessionExpiredError } from "./api-client";
import { t } from "./i18n";

export function thongDiepLoi(loi: unknown): string {
  if (loi instanceof SessionExpiredError) return loi.message;

  if (loi instanceof ApiError) {
    // 403/404: `isForbidden` gộp cả hai vì server giấu sự tồn tại của tài
    // nguyên ngoài phạm vi. Message của server ở đây thường chung chung, nên
    // dùng câu của mình cho rõ nghĩa hơn.
    if (loi.isForbidden) return t("loiQuanTri.khongDuQuyen");
    if (loi.message.trim()) return loi.message;
    return t("loiQuanTri.chung");
  }

  // Lỗi mạng (`fetch` ném `TypeError`) hoặc bất kỳ thứ gì khác.
  return t("loiQuanTri.chung");
}
