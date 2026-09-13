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
              تكاتف
            </Link>
            <p style={{ margin: "0 0 0", lineHeight: 1.9 }}>
              منصة تمويل جماعي مصرية بتوحّد المساندين بأصحاب الأفكار —
              من التعليم والصحة للبيئة والمشروعات الصغيرة.
            </p>
          </div>
          <div className="footer-col">
            <h4>استكشف</h4>
            <ul>
              <li>
                <Link to="/projects">كل المشاريع</Link>
              </li>
              {user && (
                <>
                  <li>
                    <Link to="/my-projects">مشاريعي</Link>
                  </li>
                  <li>
                    <Link to="/my-donations">تبرعاتي</Link>
                  </li>
                </>
              )}
              <li>
                <Link to="/projects/new">ابدأ حملة</Link>
              </li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>حسابك</h4>
            <ul>
              {user ? (
                <>
                  <li>
                    <Link to="/profile">الملف الشخصي</Link>
                  </li>
                  <li>
                    <Link to="/profile">إعدادات الحساب</Link>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Link to="/login">تسجيل الدخول</Link>
                  </li>
                  <li>
                    <Link to="/register">إنشاء حساب</Link>
                  </li>
                </>
              )}
            </ul>
          </div>
          <div className="footer-col">
            <h4>تواصل</h4>
            <ul>
              <li>
                <span>القاهرة، مصر</span>
              </li>
              <li>
                <span>support@takaful.example</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <span>منصة تكاتف — تمويل جماعي للمشاريع في مصر.</span>
          <span>© {new Date().getFullYear()} تكاتف. كل الحقوق محفوظة.</span>
        </div>
      </div>
    </footer>
  );
}