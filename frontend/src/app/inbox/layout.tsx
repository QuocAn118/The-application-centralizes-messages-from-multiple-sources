import { AuthGuard } from "@/components/auth-guard";
import { NavRail } from "@/components/nav-rail";

/** Khung của mọi màn `/inbox*`: nav trái + vùng nội dung (spec §4.2). */
export default function InboxLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <NavRail />
        <div className="flex min-w-0 flex-1">{children}</div>
      </div>
    </AuthGuard>
  );
}
