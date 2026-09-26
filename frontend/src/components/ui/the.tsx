/**
 * Thẻ khung ngoài: viền 2px + bóng cứng 4px. Theo đặc tả, viền dày và bóng CHỈ
 * dành cho khung ngoài; bên trong (bảng, danh sách) dùng kẻ mảnh 1px `line`.
 *
 * Thẻ không có hành vi bấm nhưng vẫn có bóng: đó là "khối nổi" của trang, không
 * phải nút. Quy tắc "có bóng = bấm được" áp cho phần tử NHỎ (nút vs nhãn).
 */

export function The({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return (
    <Tag className={`rounded-nb border-2 border-ink bg-card shadow-nb ${className}`}>
      {children}
    </Tag>
  );
}

/** Đầu thẻ: tiêu đề mục (18/700) + mô tả + hành động bên phải. */
export function TheDau({
  tieuDe,
  moTa,
  hanhDong,
}: {
  tieuDe: string;
  moTa?: string;
  hanhDong?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b-2 border-ink px-5 py-4">
      <div className="min-w-0">
        <h2 className="text-lg font-bold leading-tight text-ink">{tieuDe}</h2>
        {moTa && <p className="mt-1 text-sm text-ink-2">{moTa}</p>}
      </div>
      {hanhDong && <div className="flex shrink-0 items-center gap-2">{hanhDong}</div>}
    </div>
  );
}
