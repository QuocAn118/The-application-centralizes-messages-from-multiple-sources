"use client";

/**
 * Kết nối realtime tới `/ws/inbox` (spec §4.3, RB-2).
 *
 * Ba việc, và chỉ ba việc:
 * 1. Giữ một kết nối WS sống, mở lại có backoff khi rớt.
 * 2. **Mở lại bằng token mới khi token xoay** — WS mang access token ở query
 *    string, token cũ hết hạn thì server đóng 1008. Không làm việc này thì
 *    realtime chết âm thầm sau lần refresh đầu tiên.
 * 3. Nhận tín hiệu rồi **gọi ngược ra ngoài để refetch REST** — không bao giờ
 *    render payload WS như nội dung (RB-2): server cố ý không gửi nội dung qua
 *    WS vì việc lọc theo quyền nằm ở REST.
 */

import { useEffect, useRef } from "react";
import { API_BASE_URL, getAccessToken, onAccessTokenChange } from "./api-client";
import type { InboxSignal } from "./types";

/** Chờ tối thiểu/tối đa giữa các lần thử lại. */
const CHO_DAU_MS = 1_000;
const CHO_TOI_DA_MS = 30_000;

/**
 * Kết nối phải sống ít nhất chừng này mới coi là thành công (và reset backoff).
 *
 * Server nhận bắt tay WebSocket TRƯỚC khi xác thực token, nên token hỏng vẫn
 * kích hoạt `onopen` rồi bị đóng 1008 ngay. Không có ngưỡng này thì backoff bị
 * vô hiệu và client quay vòng mở-đóng liên tục.
 */
const SONG_DU_LAU_MS = 5_000;

/** Đổi base URL HTTP thành ws/wss. WS ở `/ws/inbox`, KHÔNG có `/api/v1`. */
export function duongDanWebSocket(baseUrl: string, token: string): string {
  const u = new URL("/ws/inbox", baseUrl);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.searchParams.set("token", token);
  return u.toString();
}

/**
 * Thời gian chờ trước lần thử lại thứ `lan`, có nhiễu ngẫu nhiên.
 *
 * Nhiễu để nhiều tab không cùng đập vào server một nhịp sau khi mạng trở lại.
 */
export function thoiGianCho(lan: number, ngauNhien = Math.random()): number {
  const co_ban = Math.min(CHO_DAU_MS * 2 ** lan, CHO_TOI_DA_MS);
  return Math.round(co_ban * (0.5 + ngauNhien * 0.5));
}

export interface TuyChonSocket {
  /** Chạy mỗi khi nhận được một tín hiệu hợp lệ. */
  onSignal: (signal: InboxSignal) => void;
  /** Tắt hẳn (ví dụ chưa đăng nhập). */
  enabled?: boolean;
}

export function useInboxSocket({ onSignal, enabled = true }: TuyChonSocket): void {
  // Giữ callback trong ref: đổi callback không được làm đứt kết nối đang chạy.
  const onSignalRef = useRef(onSignal);
  useEffect(() => {
    onSignalRef.current = onSignal;
  }, [onSignal]);

  useEffect(() => {
    if (!enabled) return;

    let socket: WebSocket | null = null;
    let hen: ReturnType<typeof setTimeout> | null = null;
    let soLanThu = 0;
    let daHuy = false;

    function dongSocketCu() {
      if (!socket) return;
      // Gỡ handler trước khi đóng: `onclose` của kết nối cũ không được kích
      // hoạt vòng thử-lại cho một kết nối mà ta đã chủ động bỏ.
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
      try {
        socket.close();
      } catch {
        // Đóng một socket đang dở dang có thể ném — không ảnh hưởng gì.
      }
      socket = null;
    }

    function henMoLai() {
      if (daHuy || hen) return;
      const cho = thoiGianCho(soLanThu);
      soLanThu += 1;
      hen = setTimeout(() => {
        hen = null;
        ketNoi();
      }, cho);
    }

    function ketNoi() {
      if (daHuy) return;

      const token = getAccessToken();
      if (!token) {
        // Chưa có token (đang khôi phục phiên): đợi sự kiện đổi token đánh thức.
        return;
      }

      dongSocketCu();
      const ws = new WebSocket(duongDanWebSocket(API_BASE_URL, token));
      socket = ws;

      let moLuc = 0;

      ws.onopen = () => {
        // KHÔNG reset bộ đếm ngay: server chấp nhận bắt tay rồi mới xác thực,
        // token hỏng thì đóng 1008 ngay sau đó. Reset ở đây sẽ biến mọi lần
        // thử thành "thành công" và tạo vòng lặp mở-đóng ~1 giây.
        moLuc = Date.now();
      };

      ws.onmessage = (e) => {
        try {
          const tin_hieu = JSON.parse(e.data as string) as InboxSignal;
          // Chỉ chấp nhận tín hiệu đúng hình dạng: payload lạ thì bỏ qua thay vì
          // để nó chạy vào lớp cache.
          if (
            tin_hieu &&
            typeof tin_hieu.conversation_id === "string" &&
            (tin_hieu.change === "new_message" || tin_hieu.change === "status_changed")
          ) {
            onSignalRef.current(tin_hieu);
          }
        } catch {
          // Không phải JSON — bỏ qua.
        }
      };

      ws.onclose = () => {
        if (socket === ws) socket = null;
        // Chỉ coi là kết nối thành công khi nó sống đủ lâu — đủ để loại trường
        // hợp server nhận bắt tay rồi đóng ngay vì token hỏng.
        if (moLuc > 0 && Date.now() - moLuc >= SONG_DU_LAU_MS) soLanThu = 0;
        henMoLai();
      };

      ws.onerror = () => {
        // `onclose` luôn theo sau `onerror`, nên để đó lo việc thử lại.
      };
    }

    ketNoi();

    // Token xoay → mở lại ngay bằng token mới, không đợi hết backoff.
    const huyNgheToken = onAccessTokenChange((token) => {
      if (daHuy) return;
      if (hen) {
        clearTimeout(hen);
        hen = null;
      }
      soLanThu = 0;
      if (token) ketNoi();
      else dongSocketCu();
    });

    return () => {
      daHuy = true;
      huyNgheToken();
      if (hen) clearTimeout(hen);
      dongSocketCu();
    };
  }, [enabled]);
}
