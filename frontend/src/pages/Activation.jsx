import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { activate } from "../api/auth";

export default function Activation() {
  const { uid, token } = useParams();
  const [status, setStatus] = useState("loading"); // loading | success | error

  useEffect(() => {
    let cancelled = false;
    activate(uid, token)
      .then(() => {
        if (!cancelled) setStatus("success");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [uid, token]);

  return (
    <div className="page" style={{ maxWidth: 480, textAlign: "center" }}>
      {status === "loading" && <p>بنفعّل حسابك...</p>}

      {status === "success" && (
        <>
          <h1 className="section-heading">اتفعّل حسابك بنجاح 🎉</h1>
          <p style={{ color: "var(--ink-600)", marginBottom: 24 }}>
            تقدر تسجّل دخول دلوقتي وتبدأ تستخدم تكاتف.
          </p>
          <Link to="/login" className="btn btn-primary">
            تسجيل الدخول
          </Link>
        </>
      )}

      {status === "error" && (
        <>
          <h1 className="section-heading">رابط التفعيل مش شغال</h1>
          <p style={{ color: "var(--ink-600)", marginBottom: 24 }}>
            ممكن يكون الرابط انتهت صلاحيته أو اتفعّل الحساب من قبل. جرب تسجّل
            دخول، ولو المشكلة استمرت اعمل حساب جديد.
          </p>
          <Link to="/login" className="btn btn-outline">
            الرجوع لتسجيل الدخول
          </Link>
        </>
      )}
    </div>
  );
}
