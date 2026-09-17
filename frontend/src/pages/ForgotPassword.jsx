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
      if (err.response?.status === 429) {
        setError("Too many attempts. Please try again later.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-side">
        <h1>Forgot Your Password?</h1>
        <p>
          No problem. Enter your email address and we will send you a link to
          create a new password.
        </p>
      </div>

      <div className="auth-form-wrap">
        <div className="auth-card">
          <h2>Reset Your Password</h2>

          {sent ? (
            <div className="form-alert success">
              If this email is registered with us, a password reset link has
              been sent to you. The link is valid for 24 hours.
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <p className="subtitle">
                We will send a password reset link to your email address.
              </p>

              {error && <div className="form-alert">{error}</div>}

              <div className="field">
                <label>Email Address</label>
                <input
                  type="email"
                  className="input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <button
                className="btn btn-primary btn-block"
                disabled={loading}
              >
                {loading ? "Sending..." : "Send Reset Link"}
              </button>
            </form>
          )}

          <p className="auth-switch">
            Remember your password? <Link to="/login">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}