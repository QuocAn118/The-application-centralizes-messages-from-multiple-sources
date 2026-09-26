/**
 * Bảng dữ liệu. Viền dày + bóng CHỈ ở khung ngoài; bên trong kẻ mảnh 1px `line`
 * giữa các hàng (đặc tả: màn nhiều dữ liệu không được rối mắt vì viền dày).
 *
 * Chỉ là lớp mặc định bọc thẻ HTML — không phải "data grid". Sắp xếp/lọc vẫn do
 * màn tự làm như trước.
 */

type P<T> = T & { className?: string };

export function Bang({ className = "", ...props }: P<React.TableHTMLAttributes<HTMLTableElement>>) {
  return (
    <div className="overflow-x-auto rounded-nb border-2 border-ink bg-card shadow-nb">
      <table className={`w-full border-collapse text-left text-sm ${className}`} {...props} />
    </div>
  );
}

export function Th({ className = "", ...props }: P<React.ThHTMLAttributes<HTMLTableCellElement>>) {
  return (
    <th
      scope="col"
      className={`border-b-2 border-ink bg-sunken px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-ink-2 ${className}`}
      {...props}
    />
  );
}

export function Td({ className = "", ...props }: P<React.TdHTMLAttributes<HTMLTableCellElement>>) {
  return <td className={`px-4 py-3 align-middle text-ink ${className}`} {...props} />;
}

export function Tr({ className = "", ...props }: P<React.HTMLAttributes<HTMLTableRowElement>>) {
  return <tr className={`border-t border-line first:border-t-0 hover:bg-paper ${className}`} {...props} />;
}
