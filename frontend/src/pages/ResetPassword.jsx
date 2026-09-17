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
      setErrors({ password: "At least 8 characters." });
      return;
    }
    if (password !== confirmPassword) {
      setErrors({ confirm_password: "Passwords do not match." });
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
        setFormError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-side">
        <h1>Choose a new password.</h1>
        <p>Make it strong — at least 8 characters, and not only numbers or a common password.</p>
      </div>
      <div className="auth-form-wrap">
        <div className="auth-card">
          <h2>New Password</h2>

          {done ? (
            <div className="form-alert success">Your password has been changed successfully. Redirecting you to the login page...</div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {formError && <div className="form-alert">{formError}</div>}

              <div className="field">
                <label>New Password</label>
                <div className="password-field">
                  <input
                    type={showPassword ? "text" : "password"}
                    className={`input${errors.password ? " has-error" : ""}`}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoFocus
                  />
                  <button type="button" className="password-toggle" onClick={() => setShowPassword((s) => !s)}>
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {errors.password && <p className="field-error">{errors.password}</p>}
              </div>

              <div className="field">
                <label>Confirm Password</label>
                <input
                  type={showPassword ? "text" : "password"}
                  className={`input${errors.confirm_password ? " has-error" : ""}`}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                {errors.confirm_password && <p className="field-error">{errors.confirm_password}</p>}
              </div>

              <button className="btn btn-primary btn-block" disabled={loading}>
                {loading ? "Saving..." : "Save New Password"}
              </button>
            </form>
          )}

          <p className="auth-switch">
            <Link to="/login">Back to Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
}