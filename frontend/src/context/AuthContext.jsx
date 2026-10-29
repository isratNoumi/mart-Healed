import React from "react";
import { getCurrentUser, login, logout, register } from "../api/auth";
import { UNAUTHORIZED_EVENT } from "../api/client";

export const AuthContext = React.createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((data) => { if (active) setUser(data.user); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setLoading(false); });

    const handleUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      active = false;
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const signIn = React.useCallback(async (credentials) => {
    const data = await login(credentials);
    setUser(data.user);
    return data.user;
  }, []);

  const signUp = React.useCallback(async (details) => {
    // Registration never reveals whether the email already exists and issues no
    // session; sign in with the submitted credentials to start one.
    await register(details);
    let data;
    try {
      data = await login({ email: details.email, password: details.password });
    } catch (error) {
      if (error && error.status === 401) {
        error.message = "We couldn't create an account with those details. If you already have an account, try signing in.";
      }
      throw error;
    }
    setUser(data.user);
    return data.user;
  }, []);

  const signOut = React.useCallback(async () => {
    try {
      await logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = React.useMemo(() => ({ user, loading, signIn, signUp, signOut }), [user, loading, signIn, signUp, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return React.useContext(AuthContext);
}
