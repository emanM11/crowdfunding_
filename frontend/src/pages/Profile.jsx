import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteAccount, getProfile, updateProfile } from "../api/auth";
import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { logout, setUser } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const previewRef = useRef(null);

  useEffect(() => {
    getProfile()
      .then(({ data }) => setForm(data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  const update = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((err) => ({ ...err, [field]: null }));
  };

  const handleAvatar = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setErrors((err) => ({ ...err, profile_picture: "الصورة أكبر من 5 ميجابايت." }));
      return;
    }
    setAvatarFile(file);
    const url = URL.createObjectURL(file);
    previewRef.current = url;
    setAvatarPreview(url);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setFormError("");
    setSaved(false);
    const formData = new FormData();
    ["first_name", "last_name", "phone_number", "birthdate", "facebook_profile", "country"].forEach((key) => {
      formData.append(key, form[key] || "");
    });
    if (avatarFile) formData.append("profile_picture", avatarFile);

    setSaving(true);
    try {
      const { data } = await updateProfile(formData);
      setForm(data);
      setUser(data);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      if (err.response?.status === 400) {
        const fieldErrors = {};
        Object.entries(err.response.data || {}).forEach(([k, v]) => {
          fieldErrors[k] = Array.isArray(v) ? v.join(" ") : String(v);
        });
        setErrors(fieldErrors);
      } else {
        setFormError("مقدرناش نحفظ التعديلات دلوقتي.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (e) => {
    e.preventDefault();
    setDeleteError("");
    try {
      await deleteAccount(deletePassword);
      logout();
      navigate("/");
    } catch (err) {
      if (err.response?.status === 400) {
        setDeleteError(err.response.data?.password?.[0] || "كلمة المرور غلط.");
      } else {
        setDeleteError("مقدرناش نحذف الحساب دلوقتي.");
      }
    }
  };

  if (loading || !form) return <div className="page">بيتم التحميل...</div>;

  return (
    <div className="page" style={{ maxWidth: 560 }}>
      <h1 className="section-heading">حسابي</h1>

      <form onSubmit={handleSave} noValidate>
        {formError && <div className="form-alert">{formError}</div>}
        {saved && <div className="form-alert success">اتحفظت التعديلات.</div>}

        <div className="avatar-picker">
          <div className="avatar-preview">
            {avatarPreview || form.profile_picture ? (
              <img src={avatarPreview || form.profile_picture} alt="" />
            ) : (
              "صورة"
            )}
          </div>
          <div>
            <label htmlFor="avatar" className="btn btn-outline" style={{ cursor: "pointer" }}>
              تغيير الصورة
            </label>
            <input id="avatar" type="file" accept="image/*" onChange={handleAvatar} style={{ display: "none" }} />
            {errors.profile_picture && <p className="field-error">{errors.profile_picture}</p>}
          </div>
        </div>

        <div className="two-col">
          <div className="field">
            <label>الاسم الأول</label>
            <input className="input" value={form.first_name} onChange={update("first_name")} />
          </div>
          <div className="field">
            <label>الاسم الأخير</label>
            <input className="input" value={form.last_name} onChange={update("last_name")} />
          </div>
        </div>

        <div className="field">
          <label>الإيميل</label>
          <input className="input" value={form.email} disabled style={{ background: "var(--sand-100)", color: "var(--ink-400)" }} />
          <p className="hint">الإيميل مينفعش يتغيّر.</p>
        </div>

        <div className="field">
          <label>رقم الموبايل</label>
          <input className={`input${errors.phone_number ? " has-error" : ""}`} value={form.phone_number} onChange={update("phone_number")} />
          {errors.phone_number && <p className="field-error">{errors.phone_number}</p>}
        </div>

        <div className="two-col">
          <div className="field">
            <label>تاريخ الميلاد (اختياري)</label>
            <input type="date" className="input" value={form.birthdate || ""} onChange={update("birthdate")} />
          </div>
          <div className="field">
            <label>الدولة (اختياري)</label>
            <input className="input" value={form.country || ""} onChange={update("country")} />
          </div>
        </div>

        <div className="field">
          <label>رابط فيسبوك (اختياري)</label>
          <input className="input" value={form.facebook_profile || ""} onChange={update("facebook_profile")} />
        </div>

        <button className="btn btn-primary" disabled={saving}>
          {saving ? "بيتم الحفظ..." : "حفظ التعديلات"}
        </button>
      </form>

      <div className="danger-zone">
        <h3>حذف الحساب</h3>
        <p>الإجراء ده نهائي. بياناتك الشخصية هتتشال، بس مشاريعك وتبرعاتك هتفضل متسجلة.</p>
        {deleteError && <div className="form-alert">{deleteError}</div>}
        {!confirmingDelete ? (
          <button className="btn btn-outline" style={{ borderColor: "var(--danger)", color: "var(--danger)" }} onClick={() => setConfirmingDelete(true)}>
            حذف حسابي
          </button>
        ) : (
          <form onSubmit={handleDelete} style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 320 }}>
            <input
              type="password"
              className="input"
              placeholder="اكتب كلمة المرور للتأكيد"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              autoFocus
            />
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn btn-primary" style={{ background: "var(--danger)", color: "#fff" }} disabled={!deletePassword}>
                متأكد، احذف الحساب نهائيًا
              </button>
              <button type="button" className="btn btn-ghost" style={{ color: "var(--ink-600)" }} onClick={() => setConfirmingDelete(false)}>
                تراجع
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
