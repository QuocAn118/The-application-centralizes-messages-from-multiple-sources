/**
 * Chặn cỡ chữ dưới 12px quay lại (yêu cầu redesign: tối thiểu 12px toàn app).
 *
 * Tailwind v4: `text-xs` = 12px là mức nhỏ nhất được phép. Test quét mọi file
 * `.tsx` tìm cỡ viết tay `text-[Npx]` / `text-[Nrem]` nhỏ hơn 12px — trước đây có
 * 19 chỗ `text-[11px]`/`text-[10px]` rải trong 15 file.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

function moiFileTsx(thuMuc: string): string[] {
  return readdirSync(thuMuc).flatMap((ten) => {
    const duong = join(thuMuc, ten);
    if (statSync(duong).isDirectory()) return moiFileTsx(duong);
    return ten.endsWith(".tsx") ? [duong] : [];
  });
}

describe("cỡ chữ tối thiểu 12px", () => {
  it("không file nào dùng text-[<12px] hoặc text-[<0.75rem]", () => {
    const vi_pham: string[] = [];
    for (const f of moiFileTsx(join(__dirname, ".."))) {
      const noiDung = readFileSync(f, "utf8");
      for (const m of noiDung.matchAll(/text-\[(\d+(?:\.\d+)?)(px|rem)\]/g)) {
        const px = m[2] === "rem" ? Number(m[1]) * 16 : Number(m[1]);
        if (px < 12) vi_pham.push(`${f}: ${m[0]}`);
      }
    }
    expect(vi_pham).toEqual([]);
  });
});
