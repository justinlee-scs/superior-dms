
import { createRoot } from "react-dom/client";
//import App from "./app/App.js";
import AuthGate from "./auth/AuthGate.js";
import { applyUiThemeClass, readUiPreferences } from "./lib/ui-preferences";
import "./styles/index.css";

const { darkMode } = readUiPreferences();
applyUiThemeClass(darkMode);

createRoot(document.getElementById("root")!).render(<AuthGate />);
  
