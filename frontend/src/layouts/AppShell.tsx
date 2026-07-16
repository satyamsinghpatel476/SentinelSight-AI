import { Link, NavLink } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            S
          </span>
          <div>
            <p className="brand-title">SentinelSight AI</p>
            <p className="brand-subtitle">Security monitoring MVP</p>
          </div>
        </div>

        <nav className="nav-list">
          <NavLink to="/">Foundation</NavLink>
          <NavLink to="/websites">Websites</NavLink>
          <NavLink to="/incidents">Incidents</NavLink>
          <NavLink to="/audit">Audit</NavLink>
          <NavLink to="/settings/ai">Settings</NavLink>
          {!user ? <NavLink to="/login">Login</NavLink> : null}
        </nav>

        <div className="session-panel">
          {user ? (
            <>
              <p className="session-name">{user.name}</p>
              <p className="session-role">{user.role.replace("_", " ")}</p>
              <button className="button button--secondary" type="button" onClick={() => void logout()}>
                Logout
              </button>
            </>
          ) : (
            <Link className="button button--secondary" to="/login">
              Sign in
            </Link>
          )}
        </div>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
}
