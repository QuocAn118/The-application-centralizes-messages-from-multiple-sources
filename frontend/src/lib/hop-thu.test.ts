import { describe, expect, it } from "vitest";
import {
  dungDongChat,
  gopTrang,
  hienSoChuaDoc,
  laChoLau,
  mocTuongDoi,
  nenDanhDauDaDoc,
  nhanCho,
  nhanNgay,
  noiDungSuKien,
  phutCho,
} from "./hop-thu";
import type { ConversationEvent, InboxItem, Message } from "./types";

// Giờ máy (không Z) để test không phụ thuộc múi giờ nơi chạy.
const BAY_GIO = new Date(2026, 8, 27, 10, 0); // Chủ nhật 27/09/2026 10:00
const luc = (ngay: number, gio: number, phut = 0) => new Date(2026, 8, ngay, gio, phut).toISOString();

describe("mocTuongDoi", () => {
  it.each([
    [new Date(2026, 8, 27, 9, 59, 30).toISOString(), "Vừa xong"],
    [luc(27, 9, 48), "12 phút"],
    [luc(27, 8, 5), "08:05"],
    [luc(26, 23, 50), "Hôm qua"],
    [luc(23, 12), "Th 4"],
    [luc(15, 12), "15/09"],
  ])("%s → %s", (iso, mong) => {
    expect(mocTuongDoi(iso, BAY_GIO)).toBe(mong);
  });

  it("qua nửa đêm: 23:59 hôm qua vẫn là 'Hôm qua' dù mới 2 giờ trước", () => {
    expect(mocTuongDoi(luc(26, 23, 59), new Date(2026, 8, 27, 1, 30))).toBe("Hôm qua");
  });
});

describe("thời gian chờ", () => {
  it("null khi không ai chờ", () => {
    expect(phutCho(null, BAY_GIO)).toBeNull();
    expect(laChoLau(null)).toBe(false);
  });

  it("ngưỡng 15 phút", () => {
    expect(laChoLau(phutCho(luc(27, 9, 46), BAY_GIO))).toBe(false); // 14
    expect(laChoLau(phutCho(luc(27, 9, 45), BAY_GIO))).toBe(true); // 15
  });

  it("đồng hồ lệch (mốc ở tương lai) không ra số âm", () => {
    expect(phutCho(luc(27, 10, 3), BAY_GIO)).toBe(0);
  });

  it("nhãn đổi đơn vị", () => {
    expect(nhanCho(12)).toBe("Chờ 12 phút");
    expect(nhanCho(125)).toBe("Chờ 2 giờ");
    expect(nhanCho(3 * 24 * 60)).toBe("Chờ 3 ngày");
  });
});

describe("gopTrang (Review Focus #5)", () => {
  const item = (id: string) => ({ conversation_id: id }) as InboxItem;

  it("hội thoại bị đẩy lên đầu giữa hai lần tải không thành hai dòng", () => {
    const trang1Moi = [item("x"), item("a"), item("b")];
    const trang2Cu = [item("c"), item("x"), item("d")];
    expect(gopTrang([trang1Moi, trang2Cu]).map((i) => i.conversation_id)).toEqual([
      "x", "a", "b", "c", "d",
    ]);
  });
});

describe("hienSoChuaDoc", () => {
  it.each([[0, ""], [1, "1"], [99, "99"], [100, "99+"]])("%i → '%s'", (n, mong) => {
    expect(hienSoChuaDoc(n)).toBe(mong);
  });
});

describe("nenDanhDauDaDoc (Review Focus #2)", () => {
  it("tab ở nền → KHÔNG đánh dấu", () => {
    expect(nenDanhDauDaDoc(true, false)).toBe(false);
  });
  it("đang mở + có focus → đánh dấu", () => {
    expect(nenDanhDauDaDoc(true, true)).toBe(true);
  });
  it("không mở hội thoại đó → không", () => {
    expect(nenDanhDauDaDoc(false, true)).toBe(false);
  });
});

const suKien = (kind: ConversationEvent["kind"], o: Partial<ConversationEvent> = {}): ConversationEvent => ({
  id: `e-${kind}`, kind, created_at: luc(27, 9), actor_name: "An", from_name: "Bình", to_name: "Chi", ...o,
});

describe("noiDungSuKien", () => {
  it.each([
    ["TAKEN", "Chi đã nhận việc"],
    ["AUTO_ASSIGNED", "Hệ thống tự giao cho Chi"],
    ["ASSIGNED", "An giao cho Chi"],
    ["REASSIGNED", "Chuyển từ Bình sang Chi"],
    ["UNASSIGNED", "Gỡ người phụ trách Bình"],
  ] as const)("%s", (kind, mong) => {
    expect(noiDungSuKien(suKien(kind))).toBe(mong);
  });

  it("thiếu tên → gạch ngang, không in 'null'", () => {
    expect(noiDungSuKien(suKien("UNASSIGNED", { from_name: null }))).toBe("Gỡ người phụ trách —");
  });
});

describe("nhanNgay", () => {
  it.each([
    [luc(27, 1), "Hôm nay"],
    [luc(26, 23), "Hôm qua"],
    [luc(14, 8), "Thứ Hai, 14/09"],
  ])("%s → %s", (iso, mong) => {
    expect(nhanNgay(iso, BAY_GIO)).toBe(mong);
  });
  it("khác năm thì thêm năm", () => {
    expect(nhanNgay(new Date(2025, 11, 31, 9).toISOString(), BAY_GIO)).toBe("Thứ Tư, 31/12/2025");
  });
});

describe("dungDongChat", () => {
  const tin = (id: string, iso: string, direction: Message["direction"] = "INBOUND", sender: string | null = null): Message => ({
    id, direction, text: id, created_at: iso, sender_user_id: sender, attachments: [],
  });

  it("gom tin liên tiếp cùng người trong 5 phút; giờ ở tin cuối nhóm", () => {
    const dong = dungDongChat(
      [tin("a", luc(27, 9, 0)), tin("b", luc(27, 9, 4)), tin("c", luc(27, 9, 10))],
      [],
      BAY_GIO,
    ).filter((d) => d.loai === "tin");
    expect(dong.map((d) => d.loai === "tin" && [d.tin.id, d.dauNhom, d.cuoiNhom])).toEqual([
      ["a", true, false],
      ["b", false, true],
      ["c", true, true], // cách b 6 phút → nhóm mới
    ]);
  });

  it("đổi chiều / đổi nhân viên gửi → nhóm mới", () => {
    const dong = dungDongChat(
      [tin("a", luc(27, 9, 0)), tin("b", luc(27, 9, 1), "OUTBOUND", "u1"), tin("c", luc(27, 9, 2), "OUTBOUND", "u2")],
      [],
      BAY_GIO,
    ).filter((d) => d.loai === "tin");
    expect(dong.every((d) => d.loai === "tin" && d.dauNhom && d.cuoiNhom)).toBe(true);
  });

  it("chèn dòng hệ thống đúng thời điểm và cắt nhóm", () => {
    const dong = dungDongChat(
      [tin("a", luc(27, 9, 0)), tin("b", luc(27, 9, 2))],
      [suKien("TAKEN", { created_at: luc(27, 9, 1) })],
      BAY_GIO,
    );
    expect(dong.map((d) => d.loai)).toEqual(["ngay", "tin", "su-kien", "tin"]);
    const b = dong[3];
    expect(b.loai === "tin" && b.dauNhom).toBe(true);
  });

  it("vạch ngày qua nửa đêm, nhóm không nối qua vạch", () => {
    const dong = dungDongChat([tin("a", luc(26, 23, 58)), tin("b", luc(27, 0, 1))], [], BAY_GIO);
    expect(dong.map((d) => (d.loai === "ngay" ? d.nhan : d.loai))).toEqual(["Hôm qua", "tin", "Hôm nay", "tin"]);
    expect(dong[3].loai === "tin" && dong[3].dauNhom).toBe(true);
  });
});
