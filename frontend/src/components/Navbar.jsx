import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { notifySuccess } from "../lib/toast";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogout = () => {
    logout();
    setOpen(false);
    notifySuccess("Logged out successfully.");
    navigate("/");
  };

  const close = () => setOpen(false);

  return (
    <header className={`navbar${scrolled ? " scrolled" : ""}`}>
      <div className="container navbar-inner">
        <Link to="/" className="brand" onClick={close}>
          <span className="dot" />
          Takatof
        </Link>

        <nav className={`nav-links${open ? " open" : ""}`}>
          <Link to="/" onClick={close}>
            Home
          </Link>
          <Link to="/projects" onClick={close}>
            Explore Projects
          </Link>
          {user ? (
            <>
              <Link to="/my-projects" onClick={close}>
                My Projects
              </Link>
              <Link to="/my-donations" onClick={close}>
                My Donations
              </Link>
              <Link to="/profile" onClick={close}>
                My Account
              </Link>
              <button className="btn btn-ghost" onClick={handleLogout}>
                Log Out
              </button>
              <Link to="/projects/new" className="btn btn-primary" onClick={close}>
                Start a Campaign
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" onClick={close}>
                Log In
              </Link>
              <Link to="/register" className="btn btn-primary" onClick={close}>
                Create Account
              </Link>
            </>
          )}
          <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme" title="Toggle theme">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </nav>

        <button
          className="nav-toggle"
          aria-label="Menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>
    </header>
  );
}