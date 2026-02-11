// ui/auth/logout.tsx
import React from "react";
import { useAuth } from "./AuthContext";

export const Logout: React.FC = () => {
    const { logout } = useAuth();

    return (
        <button onClick={logout}>
            Logout
        </button>
    );
};
