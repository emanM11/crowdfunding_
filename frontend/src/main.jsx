import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import "./index.css";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

// Prevent a FOUC before React mounts: apply the persisted theme immediately.
(() => {
  try {
    const saved = localStorage.getItem("theme");
    const dark =
      saved === "dark" ||
      (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (dark) document.documentElement.dataset.theme = "dark";
  } catch {
    /* noop */
  }
})();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster
            position="top-center"
            toastOptions={{
              duration: 3500,
              style: {
                direction: "rtl",
                background: "var(--navy-900)",
                color: "#eaf2ff",
                borderRadius: 14,
                fontWeight: 600,
              },
              success: { iconTheme: { primary: "var(--emerald-500)", secondary: "#fff" } },
              error: { iconTheme: { primary: "var(--danger)", secondary: "#fff" } },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
);