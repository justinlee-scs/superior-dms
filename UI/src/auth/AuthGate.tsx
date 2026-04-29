import { useEffect, useState } from "react";
import LoginPage from "./LoginPage";
import App from "../app/App";

/**
 * AuthGate
 * - Initializes from sessionStorage for persisted login state
 */
export default function AuthGate() {
  const [token, setToken] = useState<string | null>(sessionStorage.getItem("access_token"));

  useEffect(() => {
    setToken(sessionStorage.getItem("access_token"));
  }, []);

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
