"use client";

/**
 * Panel khách tối giản (redesign 2a §4.3): kênh, id trên nền tảng, người phụ
 * trách, phòng. Lịch sử / ghi chú / nhãn là Phần 2b — KHÔNG để ô trống chờ sẵn.
 *
 * Thu gọn được; lựa chọn nhớ trong `localStorage` (bọc try/catch — trình duyệt
 * chặn storage thì vẫn chạy, chỉ không nhớ). Chưa có lựa chọn: mở khi màn đủ
 * rộng (≥ 1440), thu gọn ở 1280 cho khung chat đủ chỗ.
 */

import { useState } from "react";
import { Check, Copy, PanelRightClose, PanelRightOpen } from "lucide-react";
import { DAU_GACH, NHAN_KENH } from "@/lib/hien-thi";
import type { Conversation } from "@/lib/types";
import { IconKenh } from "./ui/icon-kenh";
import { NutIcon } from "./ui/nut-icon";

const KHOA = "omnichat.panel-khach.mo";

function docMo(): boolean {
  try {
    const v = localStorage.getItem(KHOA);
    if (v !== null) return v === "1";
  } catch {
    // storage bị chặn — dùng mặc định theo bề ngang
  }
  return typeof window !== "undefined" && window.innerWidth >= 1440;
}

export function PanelKhach({ hoiThoai, tenPhong }: { hoiThoai: Conversation; tenPhong: string | null }) {
  const [mo, setMo] = useState(docMo);
  const [daChep, setDaChep] = useState(false);

  function doi(moi: boolean) {
    setMo(moi);
    try {
      localStorage.setItem(KHOA, moi ? "1" : "0");
    } catch {
      // không nhớ được thì thôi
    }
  }

  if (!mo) {
    return (
      <div className="flex w-12 shrink-0 flex-col items-center border-l-2 border-ink bg-card pt-3">
        <NutIcon icon={PanelRightOpen} nhan="Mở thông tin khách" onClick={() => doi(true)} />
      </div>
    );
  }

  async function chep() {
    try {
      await navigator.clipboard.writeText(hoiThoai.customer_external_id);
      setDaChep(true);
      setTimeout(() => setDaChep(false), 1500);
    } catch {
      // clipboard bị chặn (http không bảo mật) — người dùng vẫn bôi đen chép tay được
    }
  }

  return (
    <aside aria-label="Thông tin khách" className="flex w-[320px] shrink-0 flex-col border-l-2 border-ink bg-card">
      <div className="flex items-center justify-between border-b-2 border-ink px-4 py-3">
        <h2 className="text-base font-extrabold text-ink">Thông tin khách</h2>
        <NutIcon icon={PanelRightClose} nhan="Thu gọn thông tin khách" onClick={() => doi(false)} />
      </div>

      <dl className="flex flex-col gap-4 px-4 py-4 text-sm">
        <Muc nhan="Kênh">
          <span className="flex items-center gap-2 font-semibold text-ink">
            <IconKenh kenh={hoiThoai.platform} co={16} />
            {NHAN_KENH[hoiThoai.platform]}
          </span>
        </Muc>
        <Muc nhan="Id trên nền tảng">
          <span className="flex items-center gap-1">
            <code className="min-w-0 flex-1 truncate rounded-[4px] bg-sunken px-2 py-1 text-xs text-ink">
              {hoiThoai.customer_external_id || DAU_GACH}
            </code>
            {hoiThoai.customer_external_id && (
              <NutIcon icon={daChep ? Check : Copy} nhan={daChep ? "Đã chép" : "Chép id"} co="sm" onClick={() => void chep()} />
            )}
          </span>
        </Muc>
        <Muc nhan="Người phụ trách">
          <span className="font-semibold text-ink">
            {hoiThoai.assigned_user_id ? (hoiThoai.assigned_user_name ?? DAU_GACH) : "Chưa ai nhận"}
          </span>
        </Muc>
        <Muc nhan="Phòng">
          <span className="font-semibold text-ink">{tenPhong ?? "Chờ phân phòng"}</span>
        </Muc>
      </dl>
    </aside>
  );
}

function Muc({ nhan, children }: { nhan: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="mb-1 text-xs font-bold uppercase tracking-wide text-ink-2">{nhan}</dt>
      <dd>{children}</dd>
    </div>
  );
}
