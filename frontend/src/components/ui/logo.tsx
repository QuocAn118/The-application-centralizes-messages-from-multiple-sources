/**
 * Logo OmniChat "Khách mỉm cười": bong bóng chat vàng, viền + bóng cứng đen, mắt
 * vòng tròn và nụ cười móng ngựa (thiết kế user gửi 2026-09-29).
 *
 * Màu lấy từ token (`--ink`, `--accent`, `--card`) nên theo đúng design system.
 * Từ 20px trở xuống dùng bản ĐƠN GIẢN (bỏ bóng đổ, nét dày hơn, bám lưới 16px) —
 * bản đầy đủ ở cỡ đó chỉ còn là một khối mờ. Cùng hình với `app/icon.svg` và
 * `favicon.ico`.
 *
 * `nhan` có giá trị → là ảnh có tên (logo đứng một mình); bỏ trống → trang trí,
 * ẩn với trình đọc màn hình (đã có chữ "OmniChat" bên cạnh).
 */

export function Logo({ co = 40, nhan, className }: { co?: number; nhan?: string; className?: string }) {
  const aria = nhan ? { role: "img", "aria-label": nhan } : { "aria-hidden": true };
  const nho = co <= 20;
  return (
    <svg
      viewBox={nho ? "0 0 16 16" : "0 0 64 64"}
      width={co}
      height={co}
      className={className}
      {...aria}
    >
      {nho ? (
        <>
          <path d="M3.5 12.5 L1.5 15.5 L7 12.5 Z" fill="var(--ink)" />
          <rect x="1" y="1" width="14" height="12" rx="3" fill="var(--accent)" stroke="var(--ink)" strokeWidth="2" />
          <circle cx="5.5" cy="6.5" r="1.6" fill="var(--card)" stroke="var(--ink)" strokeWidth="1.5" />
          <path d="M9 6.5 A2 2 0 1 0 12 6.5" fill="none" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round" />
        </>
      ) : (
        <>
          {/* bóng cứng: khối + đuôi lệch xuống phải */}
          <rect x="8.5" y="7.5" width="51" height="45" rx="13" fill="var(--ink)" />
          <path d="M19 49 L12 62 L29 51 Z" fill="var(--ink)" />
          <path d="M15 45 L8 58 L25 47 Z" fill="var(--ink)" />
          <rect x="5.5" y="4.5" width="50" height="44" rx="12" fill="var(--accent)" stroke="var(--ink)" strokeWidth="5" />
          <circle cx="21.5" cy="23" r="5.8" fill="var(--card)" stroke="var(--ink)" strokeWidth="4" />
          <path d="M35.2 25.3 A7.5 7.5 0 1 0 44.8 25.3" fill="none" stroke="var(--ink)" strokeWidth="4" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}
