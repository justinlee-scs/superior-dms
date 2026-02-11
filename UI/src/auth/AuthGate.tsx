import { useState } from "react";
import LoginPage from "./LoginPage";
import App from "../app/App";

/**
 * AuthGate
 * - Holds token in memory only
 * - Reload clears auth automatically
 */
export default function AuthGate() {
  const [token, setToken] = useState<string | null>(null);

  if (!token) {
    return (
      <LoginPage
        onSuccess={(accessToken: string) => {
          setToken(accessToken);
        }}
      />
    );
  }

  return <App />;
}
