import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { initials } from "../constants";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-line bg-card">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded bg-signal font-mono text-sm font-medium text-white">
            #
          </span>
          <span className="text-lg font-semibold tracking-tight">Bugtracker</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 text-sm text-muted sm:flex">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink font-mono text-xs text-paper">
              {initials(user.full_name)}
            </span>
            {user.full_name}
          </span>
          <button className="btn" onClick={logout}>
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
