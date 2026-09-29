"use client";

/**
 * Biểu đồ xu hướng theo ngày (B1) — Recharts.
 *
 * Cột "Tin vào" và "Tin ra" đặt cạnh nhau mỗi ngày: khoảng hở giữa hai cột là
 * thứ người xem cần thấy (khách nhắn nhiều mà không ai trả lời). Viền mực + màu
 * đặc theo Neo-Brutalism; không bóng, không gradient.
 *
 * **Trình đọc màn hình**: SVG biểu đồ bị ẩn (`aria-hidden`), thay bằng một bảng
 * `sr-only` cùng số liệu — biểu đồ không có chữ thì người không nhìn không đọc được.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { t } from "@/lib/i18n";
import { The } from "@/components/ui/the";
import { soDem } from "@/lib/hien-thi";
import type { OverviewResponse } from "@/lib/types";

const CHU = { fontSize: 12, fill: "var(--ink-2)", fontWeight: 600 };

/** "2026-09-07" -> "07/09". */
function ngayNgan(iso: string): string {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
}

export function BieuDoXuHuong({ daily }: { daily: OverviewResponse["daily"] }) {
  return (
    <The as="figure" className="px-4 pb-3 pt-4">
      <figcaption className="mb-2 px-1 text-lg font-bold text-ink">{t("baoCao.xuHuong")}</figcaption>

      <div aria-hidden className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={daily} margin={{ top: 8, right: 8, bottom: 0, left: -8 }} barGap={2}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={ngayNgan}
              tick={CHU}
              axisLine={{ stroke: "var(--ink)", strokeWidth: 2 }}
              tickLine={false}
              minTickGap={16}
            />
            <YAxis allowDecimals={false} tick={CHU} axisLine={false} tickLine={false} width={40} />
            <Tooltip
              cursor={{ fill: "var(--sunken)" }}
              labelFormatter={(v) => `Ngày ${ngayNgan(String(v))}`}
              contentStyle={{
                border: "2px solid var(--ink)",
                borderRadius: 6,
                background: "var(--card)",
                boxShadow: "3px 3px 0 var(--ink)",
                fontSize: 13,
              }}
            />
            {/* Chữ chú giải màu MỰC: mặc định Recharts tô chữ theo màu cột, mà chữ vàng
                trên nền kem không đạt tương phản. Màu cột chỉ ở ô vuông. */}
            <Legend
              iconType="square"
              wrapperStyle={{ fontSize: 13, fontWeight: 600 }}
              formatter={(nhan) => <span style={{ color: "var(--ink)" }}>{nhan}</span>}
            />
            <Bar
              dataKey="inbound_count"
              name={t("baoCao.cotDenVao")}
              fill="var(--accent)"
              stroke="var(--ink)"
              strokeWidth={1.5}
              maxBarSize={22}
            />
            <Bar
              dataKey="outbound_count"
              name={t("baoCao.cotGuiRa")}
              fill="var(--accent-2)"
              stroke="var(--ink)"
              strokeWidth={1.5}
              maxBarSize={22}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <table className="sr-only">
        <caption>{t("baoCao.xuHuong")}</caption>
        <thead>
          <tr>
            <th scope="col">Ngày</th>
            <th scope="col">{t("baoCao.cotDenVao")}</th>
            <th scope="col">{t("baoCao.cotGuiRa")}</th>
          </tr>
        </thead>
        <tbody>
          {daily.map((d) => (
            <tr key={d.date}>
              <th scope="row">{ngayNgan(d.date)}</th>
              <td>{soDem(d.inbound_count)}</td>
              <td>{soDem(d.outbound_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </The>
  );
}
