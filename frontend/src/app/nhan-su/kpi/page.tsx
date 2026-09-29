import { ManKpi } from "@/components/nhan-su/man-kpi";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "KPI" };

/** `/nhan-su/kpi` — mọi vai; Staff chỉ thấy mục tiêu áp cho chính mình. */
export default function TrangKpi() {
  return <ManKpi />;
}
