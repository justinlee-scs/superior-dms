export type UiViewMode = "compact" | "grouped";

export type UiPreferences = {
  darkMode: boolean;
  viewMode: UiViewMode;
};

const DARK_MODE_STORAGE_KEY = "ui_dark_mode";
const VIEW_MODE_STORAGE_KEY = "ui_view_mode";

function canUseBrowserStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function readUiPreferences(): UiPreferences {
  if (!canUseBrowserStorage()) {
    return { darkMode: false, viewMode: "compact" };
  }

  const darkMode = window.localStorage.getItem(DARK_MODE_STORAGE_KEY);
  const viewMode = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);

  return {
    darkMode: darkMode === "true",
    viewMode: viewMode === "grouped" ? "grouped" : "compact",
  };
}

export function persistUiPreferences(preferences: UiPreferences) {
  if (!canUseBrowserStorage()) return;

  window.localStorage.setItem(DARK_MODE_STORAGE_KEY, String(preferences.darkMode));
  window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, preferences.viewMode);
}

export function applyUiThemeClass(darkMode: boolean) {
  if (typeof document === "undefined") return;

  document.documentElement.classList.toggle("dark", darkMode);
  document.documentElement.style.colorScheme = darkMode ? "dark" : "light";
}
