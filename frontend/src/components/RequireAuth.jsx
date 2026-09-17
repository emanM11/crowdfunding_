import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Route guard: redirects unauthenticated users to /login.
// PROJECT_SPEC.md 14 lists exactly which routes/actions need this.
export default function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Auth state is still being restored from localStorage — show a minimal
  // loader instead of a blank page (the guarded route will flash otherwise).
  if (loading) {
    return (
      <div className="page">
        <p className="empty-state">Loading...</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  return children;
}