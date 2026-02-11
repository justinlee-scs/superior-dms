// ui/auth/login.tsx
import React, { useState } from "react";
import { useAuth } from "./AuthContext";

export const Login: React.FC = () => {
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await login(email, password);
        } catch {
            setError("Login failed");
        }
    };

    return (
        <form onSubmit={onSubmit}>
            <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="email"
            />
            <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="password"
            />
            <button type="submit">Login</button>
            {error && <div>{error}</div>}
        </form>
    );
};
