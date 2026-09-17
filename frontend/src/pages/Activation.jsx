import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { activate } from "../api/auth";

export default function Activation() {
  const { uid, token } = useParams();
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    activate(uid, token)
      .then(() => {
        if (!cancelled) {
          setStatus("success");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [uid, token]);

  return (
    <div className="page" style={{ maxWidth: 480, textAlign: "center" }}>
      {status === "loading" && (
        <p>Verifying your account...</p>
      )}

      {status === "success" && (
        <>
          <h1 className="section-heading">
            Account Activated Successfully
          </h1>

          <p style={{ color: "var(--ink-600)", marginBottom: 24 }}>
            Your account is now active. You can sign in and start discovering
            projects, supporting ideas, and making a difference.
          </p>

          <Link to="/login" className="btn btn-primary">
            Sign In
          </Link>
        </>
      )}

      {status === "error" && (
        <>
          <h1 className="section-heading">
            Activation Could Not Be Completed
          </h1>

          <p style={{ color: "var(--ink-600)", marginBottom: 24 }}>
            This activation link may have expired or your account may already
            be activated. Please try signing in or register again if needed.
          </p>

          <Link to="/login" className="btn btn-outline">
            Go to Sign In
          </Link>
        </>
      )}
    </div>
  );
}
