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
    notifySuccess("تم تسجيل الخروج.");
    navigate("/");
  };

  const close = () => setOpen(false);

  return (
    <header className={`navbar${scrolled ? " scrolled" : ""}`}>
      <div className="container navbar-inner">
        <Link to="/" className="brand" onClick={close}>
          <span className="dot" />
          تكاتف
        </Link>

        <nav className={`nav-links${open ? " open" : ""}`}>
          <Link to="/projects" onClick={close}>
            استكشف المشاريع
          </Link>
          {user ? (
            <>
              <Link to="/my-projects" onClick={close}>
                مشاريعي
              </Link>
              <Link to="/my-donations" onClick={close}>
                تبرعاتي
              </Link>
              <Link to="/profile" onClick={close}>
                حسابي
              </Link>
              <button className="btn btn-ghost" onClick={handleLogout}>
                تسجيل خروج
              </button>
              <Link to="/projects/new" className="btn btn-primary" onClick={close}>
                ابدأ حملة
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" onClick={close}>
                تسجيل الدخول
              </Link>
              <Link to="/register" className="btn btn-primary" onClick={close}>
                إنشاء حساب
              </Link>
            </>
          )}
          <button className="theme-toggle" onClick={toggle} aria-label="تبديل المظهر" title="تبديل المظهر">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </nav>

        <button
          className="nav-toggle"
          aria-label="القائمة"
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