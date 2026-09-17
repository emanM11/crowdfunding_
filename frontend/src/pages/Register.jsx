import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/auth";

const EGYPT_PHONE = /^(010|011|012|015)\d{8}$/;

const initialForm = {
  first_name: "",
  last_name: "",
  email: "",
  phone_number: "",
  password: "",
  confirm_password: "",
};

export default function Register() {
  const [form, setForm] = useState(initialForm);
  const [avatar, setAvatar] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Revoke the object URL when it's replaced or the component unmounts —
  // otherwise every picked file leaks memory for the life of the tab.
  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    };
  }, [avatarPreview]);

  const update = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((err) => ({ ...err, [field]: null }));
  };

  const handleAvatar = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setErrors((err) => ({ ...err, profile_picture: "The image is larger than 5 MB." }));
      return;
    }
    setAvatar(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const validateClientSide = () => {
    const next = {};
    if (!form.first_name.trim()) next.first_name = "Required.";
    if (!form.last_name.trim()) next.last_name = "Required.";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = "Invalid email.";
    if (!EGYPT_PHONE.test(form.phone_number)) {
      next.phone_number = "Invalid Egyptian mobile number (010/011/012/015 and 11 digits).";
    }
    if (form.password.length < 8) next.password = "At least 8 characters.";
    if (form.password !== form.confirm_password) {
      next.confirm_password = "Passwords do not match.";
    }
    return next;
  };

  const applyServerErrors = (data) => {
    // DRF returns {field: [messages]} for field errors, and
    // {non_field_errors: [...]} for cross-field/password-policy errors.
    const fieldErrors = {};
    let topLevel = "";
    Object.entries(data || {}).forEach(([key, value]) => {
      const message = Array.isArray(value) ? value.join(" ") : String(value);
      if (key === "non_field_errors" || key === "detail") {
        topLevel = message;
      } else {
        fieldErrors[key] = message;
      }
    });
    setErrors(fieldErrors);
    setFormError(topLevel);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    const clientErrors = validateClientSide();
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors);
      return;
    }

    const formData = new FormData();
    Object.entries(form).forEach(([key, value]) => formData.append(key, value));
    if (avatar) formData.append("profile_picture", avatar);

    setLoading(true);
    try {
      await register(formData);
      setSubmitted(true);
    } catch (err) {
      if (err.response?.status === 400) {
        applyServerErrors(err.response.data);
      } else if (err.response?.status === 429) {
        setFormError("Too many attempts in a short time — please try again later.");
      } else {
        setFormError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="auth-shell">
        <AuthSide />
        <div className="auth-form-wrap">
          <div className="auth-card">
            <h2>Check Your Email</h2>
            <div className="form-alert success">
              We sent you an activation link to <strong>{form.email}</strong>. You must activate
              your account before you can log in — the link is valid for 24 hours.
            </div>
            <Link to="/login" className="btn btn-outline btn-block">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <AuthSide />
      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <h2>Create Account</h2>
          <p className="subtitle">Start your campaign or support a project that makes a difference.</p>

          {formError && <div className="form-alert">{formError}</div>}

          <div className="avatar-picker">
            <div className="avatar-preview">
              {avatarPreview ? <img src={avatarPreview} alt="" /> : "Photo"}
            </div>
            <div>
              <label htmlFor="avatar" className="btn btn-outline" style={{ cursor: "pointer" }}>
                Choose Photo (Optional)
              </label>
              <input
                id="avatar"
                type="file"
                accept="image/*"
                onChange={handleAvatar}
                style={{ display: "none" }}
              />
              {errors.profile_picture && <p className="field-error">{errors.profile_picture}</p>}
            </div>
          </div>

          <div className="two-col">
            <Field label="First Name" error={errors.first_name}>
              <input className={`input${errors.first_name ? " has-error" : ""}`} value={form.first_name} onChange={update("first_name")} autoComplete="given-name" />
            </Field>
            <Field label="Last Name" error={errors.last_name}>
              <input className={`input${errors.last_name ? " has-error" : ""}`} value={form.last_name} onChange={update("last_name")} autoComplete="family-name" />
            </Field>
          </div>

          <Field label="Email" error={errors.email}>
            <input type="email" className={`input${errors.email ? " has-error" : ""}`} value={form.email} onChange={update("email")} autoComplete="email" />
          </Field>

          <Field label="Mobile Number" error={errors.phone_number}>
            <input className={`input${errors.phone_number ? " has-error" : ""}`} value={form.phone_number} onChange={update("phone_number")} placeholder="01xxxxxxxxx" autoComplete="tel" />
          </Field>

          <Field label="Password" error={errors.password}>
            <div className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                className={`input${errors.password ? " has-error" : ""}`}
                value={form.password}
                onChange={update("password")}
                autoComplete="new-password"
              />
              <button type="button" className="password-toggle" onClick={() => setShowPassword((s) => !s)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <p className="hint">At least 8 characters, and not only numbers or a common password.</p>
          </Field>

          <Field label="Confirm Password" error={errors.confirm_password}>
            <input
              type={showPassword ? "text" : "password"}
              className={`input${errors.confirm_password ? " has-error" : ""}`}
              value={form.confirm_password}
              onChange={update("confirm_password")}
              autoComplete="new-password"
            />
          </Field>

          <button className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Creating..." : "Create Account"}
          </button>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Log In</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}

function AuthSide() {
  return (
    <div className="auth-side">
      <h1>Your project doesn't have to be big to make a difference.</h1>
      <p>
        Takatof connects idea creators with people ready to support them — education, health,
        or any idea that solves a real problem. Sign up and explore the projects currently running.
      </p>
    </div>
  );
}