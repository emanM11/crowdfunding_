import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Footer() {
  const { user } = useAuth();
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-col footer-brand">
            <Link to="/" className="brand">
              <span className="dot" />
              Takatof
            </Link>
            <p style={{ margin: "0 0 0", lineHeight: 1.9 }}>
              An Egyptian crowdfunding platform that connects supporters with idea creators —
              from education and healthcare to the environment and small businesses.
            </p>
          </div>
          <div className="footer-col">
            <h4>Explore</h4>
            <ul>
              <li>
                <Link to="/projects">All Projects</Link>
              </li>
              {user && (
                <>
                  <li>
                    <Link to="/my-projects">My Projects</Link>
                  </li>
                  <li>
                    <Link to="/my-donations">My Donations</Link>
                  </li>
                </>
              )}
              <li>
                <Link to="/projects/new">Start a Campaign</Link>
              </li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Your Account</h4>
            <ul>
              {user ? (
                <>
                  <li>
                    <Link to="/profile">Profile</Link>
                  </li>
                  <li>
                    <Link to="/profile">Account Settings</Link>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Link to="/login">Log In</Link>
                  </li>
                  <li>
                    <Link to="/register">Create Account</Link>
                  </li>
                </>
              )}
            </ul>
          </div>
          <div className="footer-col">
            <h4>Contact</h4>
            <ul>
              <li>
                <span>Cairo, Egypt</span>
              </li>
              <li>
                <span>support@takaful.example</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>Takatof — Crowdfunding platform for projects in Egypt.</span>
          <span>© {new Date().getFullYear()} Takatof. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}