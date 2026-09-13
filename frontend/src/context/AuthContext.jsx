import { createContext, useContext, useEffect, useState } from "react";
import { getProfile, login as loginRequest } from "../api/auth";

const AuthContext = createContext(null);

// Wraps the whole app (see main.jsx). Holds the JWT + current user, and
// exposes login/logout so any page/component can call useAuth().
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    getProfile()
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await loginRequest(email, password);
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    const { data: profile } = await getProfile();
    setUser(profile);
    return profile;
  };

  // Shared by any flow that ends with a raw JWT pair instead of
  // email+password — currently just Facebook login.
  const applyTokens = async ({ access, refresh }) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    const { data: profile } = await getProfile();
    setUser(profile);
    return profile;
  };

  const logout = () => {
    // Stateless JWT -> nothing to invalidate server-side (PROJECT_SPEC.md 7).
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, applyTokens, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
