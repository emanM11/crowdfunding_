import { useEffect, useState } from "react";
import { listCategories } from "../api/projects";

const MAX_IMAGE_MB = 5;
const MAX_IMAGES = 10;

export default function ProjectForm({ initial, onSubmit, submitLabel, existingImages = [] }) {
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    title: initial?.title || "",
    details: initial?.details || "",
    category: initial?.category?.id || "",
    total_target: initial?.total_target || "",
    start_date: initial?.start_date || "",
    end_date: initial?.end_date || "",
  });
  const [tags, setTags] = useState(initial?.tags?.map((t) => t.name) || []);
  const [tagInput, setTagInput] = useState("");
  const [images, setImages] = useState([]); // File objects (new uploads)
  const [previews, setPreviews] = useState([]); // object URLs
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listCategories().then(({ data }) => setCategories(data)).catch(() => {});
  }, []);

  useEffect(() => {
    return () => previews.forEach((url) => URL.revokeObjectURL(url));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    setErrors((err) => ({ ...err, [field]: null }));
  };

  const addTag = (e) => {
    if (e.key !== "Enter" && e.type !== "click") return;
    e.preventDefault();
    const value = tagInput.trim();
    if (value && !tags.includes(value)) setTags((t) => [...t, value]);
    setTagInput("");
  };

  const removeTag = (name) => setTags((t) => t.filter((x) => x !== name));

  const handleFiles = (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = ""; // allow re-selecting the same file later
    const room = MAX_IMAGES - images.length;
    const accepted = [];
    for (const file of files.slice(0, room)) {
      if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
        setErrors((err) => ({ ...err, images: `كل صورة لازم تكون أقل من ${MAX_IMAGE_MB}MB.` }));
        continue;
      }
      accepted.push(file);
    }
    setImages((prev) => [...prev, ...accepted]);
    setPreviews((prev) => [...prev, ...accepted.map((f) => URL.createObjectURL(f))]);
  };

  const removeImage = (idx) => {
    URL.revokeObjectURL(previews[idx]);
    setImages((prev) => prev.filter((_, i) => i !== idx));
    setPreviews((prev) => prev.filter((_, i) => i !== idx));
  };

  const validate = () => {
    const next = {};
    if (!form.title.trim()) next.title = "مطلوب.";
    if (!form.details.trim()) next.details = "مطلوب.";
    if (!form.category) next.category = "اختر فئة.";
    if (!(Number(form.total_target) > 0)) next.total_target = "لازم يكون رقم أكبر من صفر.";
    if (!form.start_date) next.start_date = "مطلوب.";
    if (!form.end_date) next.end_date = "مطلوب.";
    if (form.start_date && form.end_date && form.end_date <= form.start_date) {
      next.end_date = "لازم يكون بعد تاريخ البداية.";
    }
    return next;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    const clientErrors = validate();
    if (Object.keys(clientErrors).length) {
      setErrors(clientErrors);
      return;
    }

    const formData = new FormData();
    Object.entries(form).forEach(([key, value]) => formData.append(key, value));
    tags.forEach((t) => formData.append("tags", t));
    images.forEach((img) => formData.append("images", img));

    setLoading(true);
    try {
      await onSubmit(formData);
    } catch (err) {
      if (err.response?.status === 400) {
        const data = err.response.data;
        const fieldErrors = {};
        let topLevel = "";
        Object.entries(data || {}).forEach(([key, value]) => {
          const message = Array.isArray(value) ? value.join(" ") : String(value);
          if (key === "non_field_errors" || key === "detail") topLevel = message;
          else fieldErrors[key] = message;
        });
        setErrors(fieldErrors);
        setFormError(topLevel);
      } else {
        setFormError("حصل خطأ غير متوقع. حاول تاني.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="form-page" onSubmit={handleSubmit} noValidate>
      {formError && <div className="form-alert">{formError}</div>}

      <div className="field">
        <label>عنوان المشروع</label>
        <input className={`input${errors.title ? " has-error" : ""}`} value={form.title} onChange={update("title")} />
        {errors.title && <p className="field-error">{errors.title}</p>}
      </div>

      <div className="field">
        <label>التفاصيل</label>
        <textarea rows={6} className={`input${errors.details ? " has-error" : ""}`} value={form.details} onChange={update("details")} />
        {errors.details && <p className="field-error">{errors.details}</p>}
      </div>

      <div className="two-col">
        <div className="field">
          <label>الفئة</label>
          <select className={`input${errors.category ? " has-error" : ""}`} value={form.category} onChange={update("category")}>
            <option value="">اختر فئة</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {errors.category && <p className="field-error">{errors.category}</p>}
        </div>
        <div className="field">
          <label>الهدف المالي (ج.م)</label>
          <input type="number" min="1" step="0.01" className={`input${errors.total_target ? " has-error" : ""}`} value={form.total_target} onChange={update("total_target")} />
          {errors.total_target && <p className="field-error">{errors.total_target}</p>}
        </div>
      </div>

      <div className="two-col">
        <div className="field">
          <label>تاريخ البداية</label>
          <input type="date" className={`input${errors.start_date ? " has-error" : ""}`} value={form.start_date} onChange={update("start_date")} />
          {errors.start_date && <p className="field-error">{errors.start_date}</p>}
        </div>
        <div className="field">
          <label>تاريخ النهاية</label>
          <input type="date" className={`input${errors.end_date ? " has-error" : ""}`} value={form.end_date} onChange={update("end_date")} />
          {errors.end_date && <p className="field-error">{errors.end_date}</p>}
        </div>
      </div>

      <div className="field">
        <label>التاجات</label>
        <div className="tag-input-row">
          {tags.map((t) => (
            <span key={t} className="tag-chip" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              #{t}
              <button type="button" onClick={() => removeTag(t)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--teal-700)" }}>
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="input" placeholder="اكتب تاج واضغط Enter" value={tagInput} onChange={(e) => setTagInput(e.target.value)} onKeyDown={addTag} />
          <button type="button" className="btn btn-outline" onClick={addTag}>
            إضافة
          </button>
        </div>
      </div>

      {existingImages.length > 0 && (
        <div className="field">
          <label>الصور الحالية</label>
          <div className="image-preview-grid">
            {existingImages.map((img) => (
              <div className="thumb-wrap" key={img.id}>
                <img src={img.image} alt="" />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="field">
        <label>{existingImages.length ? "أضف صور جديدة" : "صور المشروع"}</label>
        <label htmlFor="images" className="image-drop" style={{ display: "block" }}>
          اضغط لاختيار صور (حتى {MAX_IMAGES}، أقل من {MAX_IMAGE_MB}MB لكل صورة)
        </label>
        <input id="images" type="file" accept="image/*" multiple onChange={handleFiles} style={{ display: "none" }} />
        {errors.images && <p className="field-error">{errors.images}</p>}
        {previews.length > 0 && (
          <div className="image-preview-grid">
            {previews.map((url, i) => (
              <div className="thumb-wrap" key={url}>
                <img src={url} alt="" />
                <button type="button" className="remove" onClick={() => removeImage(i)}>
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn btn-primary btn-block" disabled={loading}>
        {loading ? "بيتم الحفظ..." : submitLabel}
      </button>
    </form>
  );
}
