
  import { createRoot } from "react-dom/client";
  //import App from "./app/App.js";
  import AuthGate from "./auth/AuthGate.js";
  import "./styles/index.css";

  createRoot(document.getElementById("root")!).render(<AuthGate />);
  