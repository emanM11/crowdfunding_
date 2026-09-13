import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import FacebookLoginButton from "../components/FacebookLoginButton";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      const redirectTo = location.state?.from?.pathname || "/";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err.response?.status === 401) {
        // Deliberately generic — never reveal whether the email exists,
        // is unactivated, or the password is wrong; that distinction is
        // exactly what credential-stuffing tools probe for.
        setError("الإيميل أو كلمة المرور غلط، أو الحساب لسه متفعّلش.");
      } else if (err.response?.status === 429) {
        setError("محاولات كتير — جرب تاني بعد دقيقة.");
      } else {
        setError("حصل خطأ غير متوقع. حاول تاني.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-side">
        <h1>أهلاً بيك تاني.</h1>
        <p>سجّل دخولك عشان تتابع مشاريعك، تبرعاتك، وتكمل حملتك.</p>
      </div>
      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <h2>تسجيل الدخول</h2>
          <p className="subtitle">ادخل بياناتك عشان تكمل.</p>

          {error && <div className="form-alert">{error}</div>}

          <div className="field">
            <label>الإيميل</label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="field">
            <label>كلمة المرور</label>
            <div className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button type="button" className="password-toggle" onClick={() => setShowPassword((s) => !s)}>
                {showPassword ? "إخفاء" : "إظهار"}
              </button>
            </div>
          </div>

          <div className="field" style={{ textAlign: "left" }}>
            <Link to="/forgot-password" style={{ fontSize: "0.82rem", color: "var(--teal-700)" }}>
              نسيت كلمة المرور؟
            </Link>
          </div>

          <button className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "جاري الدخول..." : "تسجيل الدخول"}
          </button>

          <div style={{ margin: "16px 0" }}>
            <FacebookLoginButton />
          </div>

          <p className="auth-switch">
            لسه معملتش حساب؟ <Link to="/register">إنشاء حساب جديد</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
