import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">EL</span>
            </div>
            <span className="font-semibold text-lg text-slate-900">EvidenceLens AI</span>
          </Link>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <span className="text-sm text-slate-600">{user.full_name}</span>
                <button
                  onClick={() => { logout(); navigate("/login"); }}
                  className="text-sm text-slate-500 hover:text-slate-700"
                >
                  Sign out
                </button>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
