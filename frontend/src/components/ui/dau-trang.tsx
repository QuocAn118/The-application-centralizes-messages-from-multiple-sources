/**
 * Đầu trang: tiêu đề 28/800 + mô tả ngắn + nút chính bên phải (X6, X7).
 * Một mẫu duy nhất cho mọi màn — trước đây màn thì đặt tiêu đề ngoài thẻ, màn
 * thì đặt trong thẻ.
 */

export function DauTrang({
  tieuDe,
  moTa,
  hanhDong,
}: {
  tieuDe: string;
  moTa?: string;
  hanhDong?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-6">
      <div className="min-w-0">
        <h1 className="text-[28px] font-extrabold leading-tight tracking-tight text-ink">
          {tieuDe}
        </h1>
        {moTa && <p className="mt-1 max-w-[65ch] text-sm text-ink-2">{moTa}</p>}
      </div>
      {hanhDong && <div className="flex shrink-0 items-center gap-2">{hanhDong}</div>}
    </div>
  );
}
