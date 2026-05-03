import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import "@/i18n";
import App from "@/App";
import { registerServiceWorker, attachInstallPrompt } from "@/lib/push";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if (typeof window !== "undefined") {
  attachInstallPrompt();
  if (process.env.NODE_ENV === "production") {
    window.addEventListener("load", () => registerServiceWorker());
  }
}
