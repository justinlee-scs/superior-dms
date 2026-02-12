// File: authcontext.tsx
import React, { createContext, useContext, useState } from "react";
import { loginRequest } from "./loginService";

export type User = { id: string; email: string; roles: string[] };

type AuthContextType = {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: string) => boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [token, setToken] = useState<string | null>(
    sessionStorage.getItem("access_token")
  );
  const [user, setUser] = useState<User | null>(
    sessionStorage.getItem("user")
      ? JSON.parse(sessionStorage.getItem("user")!)
      : null
  );

  const login = async (email: string, password: string) => {
    const { access_token, user } = await loginRequest(email, password);
    setToken(access_token);
    setUser(user);

    // Persist token & user
    sessionStorage.setItem("access_token", access_token);
    console.log("Token from sessionStorage:", token);
    sessionStorage.setItem("user", JSON.stringify(user));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");

    // Force page reload
    window.location.reload();
  };

  const hasRole = (role: string) => user?.roles.includes(role) ?? false;

  return (
    <AuthContext.Provider value={{ token, user, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
