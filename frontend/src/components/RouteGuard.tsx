import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LoadingState } from "./ui";
import type { UserRole } from "../api/types";

interface RouteGuardProps {
  children: React.ReactNode;
  roles?: UserRole[];
}

/** Redirects to /login when unauthenticated, and to / when the role doesn't match. */
export function RouteGuard({ children, roles }: RouteGuardProps) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingState label="Checking session…" />;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
