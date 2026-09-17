import { useState } from "react"; 
import { Link, useLocation, useNavigate } from "react-router-dom"; 
import { useAuth } from "../context/AuthContext"; 
 
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
        setError("Invalid email or password, or your account is not activated yet."); 
      } else if (err.response?.status === 429) { 
        setError("Too many attempts — please try again in a minute."); 
      } else { 
        setError("An unexpected error occurred. Please try again."); 
      } 
    } finally { 
      setLoading(false); 
    } 
  }; 
 
  return ( 
    <div className="auth-shell"> 
      <div className="auth-side"> 
        <h1>Welcome Back.</h1> 
        <p>Log in to follow your projects, donations, and continue your campaign.</p> 
      </div> 
      <div className="auth-form-wrap"> 
        <form className="auth-card" onSubmit={handleSubmit} noValidate> 
          <h2>Log In</h2> 
          <p className="subtitle">Enter your details to continue.</p> 
 
          {error && <div className="form-alert">{error}</div>} 
 
          <div className="field"> 
            <label>Email</label> 
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
            <label>Password</label> 
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
                {showPassword ? "Hide" : "Show"} 
              </button> 
            </div> 
          </div> 
 
          <div className="field" style={{ textAlign: "left" }}> 
            <Link to="/forgot-password" style={{ fontSize: "0.82rem", color: "var(--teal-700)" }}> 
              Forgot your password? 
            </Link> 
          </div> 
 
          <button className="btn btn-primary btn-block" disabled={loading}> 
            {loading ? "Logging in..." : "Log In"} 
          </button> 
 
          <p className="auth-switch"> 
            Don't have an account yet? <Link to="/register">Create a new account</Link> 
          </p> 
        </form> 
      </div> 
    </div> 
  ); 
}