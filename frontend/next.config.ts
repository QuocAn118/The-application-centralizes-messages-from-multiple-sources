import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Cho phép mở app dev qua `127.0.0.1` chứ không chỉ `localhost`.
   *
   * Next 16 mặc định chặn tài nguyên dev từ origin khác, nên mở bằng
   * `http://127.0.0.1:3000` sẽ nhận 403 cho `/_next/*` và HMR đứt — trong khi
   * `NEXT_PUBLIC_API_BASE_URL` lại trỏ tới `127.0.0.1`, nên dùng lẫn hai tên là
   * chuyện thường gặp (và gây lỗi CORS khó hiểu khi FE ở `localhost` còn API ở
   * `127.0.0.1`).
   *
   * **Chỉ có tác dụng ở `next dev`**, không ảnh hưởng bản build.
   */
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
