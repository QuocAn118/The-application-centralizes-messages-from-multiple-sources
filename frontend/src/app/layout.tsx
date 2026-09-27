import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// Font của design system, có sẵn bộ chữ tiếng Việt (dấu không bị vỡ).
const beVietnamPro = Be_Vietnam_Pro({
  variable: "--font-be-vietnam-pro",
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "OmniChat · Hộp thư đa kênh",
  description: "Tập trung tin nhắn từ Zalo, Facebook, Instagram, Telegram về một hộp thư.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className={`${beVietnamPro.variable} h-full antialiased`}>
      {/* Chỉ làm desktop (quyết định redesign #3/#6): hẹp hơn 1280px thì cuộn
          ngang thay vì bẻ layout. */}
      <body className="flex min-h-full min-w-[1280px] flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
