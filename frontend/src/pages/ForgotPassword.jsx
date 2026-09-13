import { useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await requestPasswordReset(email);
      // Always shown regardless of whether the email exists — the backend
      // deliberately returns the same response either way.
      setSent(true);
    } catch (err) {
      if (err.response?.status === 429) setError("محاولات كتير — جرب تاني بعد شوية.");
      else setError("حصل خطأ غير متوقع. حاول تاني.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-side">
        <h1>نسيت كلمة المرور؟</h1>
        <p>مفيش مشكلة، اكتب إيميلك وهنبعتلك رابط تختار بيه كلمة مرور جديدة.</p>
      </div>
      <div className="auth-form-wrap">
        <div className="auth-card">
          <h2>استعادة كلمة المرور</h2>

          {sent ? (
            <div className="form-alert success">
              لو الإيميل ده مسجّل عندنا، وصلك رابط استعادة كلمة المرور — الرابط صالح لمدة 24 ساعة.
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <p className="subtitle">هنبعتلك رابط استعادة على إيميلك.</p>
              {error && <div className="form-alert">{error}</div>}
              <div className="field">
                <label>الإيميل</label>
                <input type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
              </div>
              <button className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "بيتم الإرسال..." : "إرسال رابط الاستعادة"}
              </button>
            </form>
          )}

          <p className="auth-switch">
            رجعت فاكر كلمة المرور؟ <Link to="/login">تسجيل الدخول</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
