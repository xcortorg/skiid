import { AdminDashboard } from "./admin-dashboard";

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-black/40 border-l border-white/5">
      <div className="p-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold">Admin Dashboard</h2>
            <p className="text-white/60 mt-1">
              Manage users, invites, and system settings
            </p>
          </div>
        </div>
        <AdminDashboard />
      </div>
    </div>
  );
}
