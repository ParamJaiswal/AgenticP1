import { Sidebar } from "./Sidebar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main
        className="flex-1 flex flex-col min-h-screen"
        style={{ marginLeft: "var(--sidebar-width)" }}
      >
        {children}
      </main>
    </div>
  );
}
