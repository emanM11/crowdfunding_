import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { facebookLogin } from "../api/auth";
import { useAuth } from "../context/AuthContext";

const APP_ID = import.meta.env.VITE_FACEBOOK_APP_ID;

let sdkPromise = null;
function loadFacebookSdk() {
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    if (window.FB) return resolve(window.FB);
    window.fbAsyncInit = () => {
      window.FB.init({ appId: APP_ID, cookie: false, xfbml: false, version: "v19.0" });
      resolve(window.FB);
    };
    const script = document.createElement("script");
    script.src = "https://connect.facebook.net/ar_AR/sdk.js";
    script.onerror = reject;
    document.body.appendChild(script);
  });
  return sdkPromise;
}

export default function FacebookLoginButton() {
  const { applyTokens } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // No real Facebook App ID configured for this project yet — show a
  // disabled, explanatory button instead of a broken/misleading one.
  if (!APP_ID) {
    return (
      <button type="button" className="btn btn-outline btn-block" disabled title="محتاج Facebook App ID حقيقي في إعدادات المشروع">
        الدخول بفيسبوك (محتاج إعداد لاحقًا)
      </button>
    );
  }

  const handleClick = () => {
    setError("");
    setLoading(true);
    loadFacebookSdk()
      .then(
        (FB) =>
          new Promise((resolve, reject) => {
            FB.login(
              (response) => {
                if (response.authResponse?.accessToken) resolve(response.authResponse.accessToken);
                else reject(new Error("cancelled"));
              },
              { scope: "email,public_profile" }
            );
          })
      )
      .then((accessToken) => facebookLogin(accessToken))
      .then(({ data }) => applyTokens(data))
      .then(() => navigate("/"))
      .catch((err) => {
        if (err.message !== "cancelled") {
          setError(err.response?.data?.detail || "مقدرناش نكمل الدخول بفيسبوك دلوقتي.");
        }
      })
      .finally(() => setLoading(false));
  };

  return (
    <>
      <button type="button" className="btn btn-outline btn-block" onClick={handleClick} disabled={loading}>
        {loading ? "بيتم الدخول..." : "الدخول بفيسبوك"}
      </button>
      {error && <p className="field-error">{error}</p>}
    </>
  );
}
