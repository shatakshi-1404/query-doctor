import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

function initialTheme(): "light" | "dark" {
  const saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium ${
    isActive
      ? "text-slate-900 dark:text-white"
      : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
  }`;

export default function Navbar() {
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="text-lg font-bold tracking-tight">QueryDoctor</span>
          <nav className="flex gap-4">
            <NavLink to="/" end className={linkClass}>
              Analyze
            </NavLink>
            <NavLink to="/compare" className={linkClass}>
              Compare
            </NavLink>
            <NavLink to="/history" className={linkClass}>
              History
            </NavLink>
          </nav>
        </div>
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700"
          aria-label="Toggle light and dark theme"
        >
          {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
        </button>
      </div>
    </header>
  );
}
