import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function AppLayout() {
  return (
    <div className="relative flex min-h-screen bg-bg">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,rgba(30,111,255,0.08),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(30,111,255,0.05),transparent_40%)]" />
      <Sidebar />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 px-6 py-6 md:px-8">
          <div className="mx-auto w-full max-w-[1360px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
