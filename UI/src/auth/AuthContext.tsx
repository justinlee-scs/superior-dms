import React, { createContext, useContext, useState } from "react";
import { loginRequest } from "./loginService";

export type User = {
  id: string;
  email: string;
  roles: string[];
};

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
  // In-memory only — reload clears auth
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  const login = async (email: string, password: string) => {
    const { access_token, user } = await loginRequest(email, password);

    setToken(access_token);
    setUser(user);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const hasRole = (role: string) => {
    return !!user?.roles.includes(role);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
};
