import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/auth";

export default function ResetPassword() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setErrors({});

    if (password.length < 8) {
      setErrors({ password: "8 حروف على الأقل." });
      return;
    }
    if (password !== confirmPassword) {
      setErrors({ confirm_password: "كلمتا المرور مش متطابقتين." });
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(uid, token, password, confirmPassword);
      setDone(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) {
      const data = err.response?.data;
      if (err.response?.status === 400 && data) {
        const fieldErrors = {};
        let topLevel = "";
        Object.entries(data).forEach(([key, value]) => {
          const message = Array.isArray(value) ? value.join(" ") : String(value);
          if (key === "non_field_errors" || key === "detail" || key === "confirm_password") {
            topLevel = topLevel || message;
            if (key === "confirm_password") fieldErrors.confirm_password = message;
          } else {
            fieldErrors[key] = message;
          }
        });
        setErrors(fieldErrors);
        setFormError(topLevel && !fieldErrors.confirm_password ? topLevel : "");
      } else {
        setFormError("حصل خطأ غير متوقع. حاول تاني.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-side">
        <h1>اختار كلمة مرور جديدة.</h1>
        <p>خليها قوية — 8 حروف على الأقل، وميكونش رقم بس أو باسورد شائع.</p>
      </div>
      <div className="auth-form-wrap">
        <div className="auth-card">
          <h2>كلمة مرور جديدة</h2>

          {done ? (
            <div className="form-alert success">اتغيّرت كلمة المرور بنجاح، هنودّيك لصفحة الدخول...</div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {formError && <div className="form-alert">{formError}</div>}

              <div className="field">
                <label>كلمة المرور الجديدة</label>
                <div className="password-field">
                  <input
                    type={showPassword ? "text" : "password"}
                    className={`input${errors.password ? " has-error" : ""}`}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoFocus
                  />
                  <button type="button" className="password-toggle" onClick={() => setShowPassword((s) => !s)}>
                    {showPassword ? "إخفاء" : "إظهار"}
                  </button>
                </div>
                {errors.password && <p className="field-error">{errors.password}</p>}
              </div>

              <div className="field">
                <label>تأكيد كلمة المرور</label>
                <input
                  type={showPassword ? "text" : "password"}
                  className={`input${errors.confirm_password ? " has-error" : ""}`}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                {errors.confirm_password && <p className="field-error">{errors.confirm_password}</p>}
              </div>

              <button className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "بيتم الحفظ..." : "حفظ كلمة المرور الجديدة"}
              </button>
            </form>
          )}

          <p className="auth-switch">
            <Link to="/login">الرجوع لتسجيل الدخول</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
