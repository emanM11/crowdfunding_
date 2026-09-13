import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, CalendarDays, Flag, Gift, History } from "lucide-react";
import {
  addProjectUpdate,
  addRewardTier,
  cancelProject,
  getProject,
} from "../api/projects";
import { rateProject, reportContent } from "../api/core";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import StarRating from "../components/StarRating";
import ProjectCard from "../components/ProjectCard";
import CommentsSection from "../components/CommentsSection";
import DonationModal from "../components/DonationModal";
import { notifyError, notifySuccess } from "../lib/toast";

function formatDate(isoDate) {
  if (!isoDate) return "";
  return new Date(isoDate).toLocaleDateString("ar-EG", { year: "numeric", month: "long", day: "numeric" });
}

export default function ProjectDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [activeImage, setActiveImage] = useState(0);
  const [activeTab, setActiveTab] = useState("story");
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);

  const [showDonate, setShowDonate] = useState(false);
  const [donateAmount, setDonateAmount] = useState("");

  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const [cancelError, setCancelError] = useState("");

  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState("");

  const [updateTitle, setUpdateTitle] = useState("");
  const [updateBody, setUpdateBody] = useState("");
  const [postingUpdate, setPostingUpdate] = useState(false);

  const [tierTitle, setTierTitle] = useState("");
  const [tierDesc, setTierDesc] = useState("");
  const [tierAmount, setTierAmount] = useState("");
  const [postingTier, setPostingTier] = useState(false);

  const load = () => {
    setLoading(true);
    getProject(id)
      .then(({ data }) => {
        setProject(data);
        setActiveImage(0);
      })
      .catch((err) => {
        if (err.response?.status === 404) setNotFound(true);
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  if (loading) {
    return (
      <div className="page">
        <div className="detail-grid">
          <div>
            <div className="gallery-main skeleton" />
            <div style={{ height: 34, margin: "22px 0 6px" }}>
              <div className="skeleton sk-line" style={{ width: "55%", height: 26 }} />
            </div>
            <div className="skeleton detail-body" style={{ height: 160 }} />
          </div>
          <aside className="donate-card">
            <div className="skeleton sk-line" style={{ width: "60%" }} />
            <div className="skeleton sk-line" style={{ width: "45%", marginTop: 10 }} />
            <div className="skeleton sk-line" style={{ width: "100%", marginTop: 18 }} />
            <div className="skeleton sk-line" style={{ width: "70%", marginTop: 18 }} />
          </aside>
        </div>
      </div>
    );
  }
  if (notFound) {
    return (
      <div className="page" style={{ textAlign: "center" }}>
        <h1 className="section-heading">المشروع ده مش موجود</h1>
        <Link to="/projects" className="btn btn-outline">
          كل المشاريع
        </Link>
      </div>
    );
  }
  if (!project) return null;

  const target = Number(project.total_target) || 0;
  const raised = Number(project.total_donations) || 0;
  const pct = target > 0 ? Math.min(100, Math.round((raised / target) * 100)) : 0;
  const isCreator = user && project.creator.id === user.id;
  const canDonate = user && !isCreator && project.status === "running";
  const canCancel = isCreator && project.status === "running" && (target > 0 ? raised / target < 0.25 : false);
  const images = project.images || [];
  const daysLeft = project.status === "running"
    ? Math.max(0, Math.ceil((new Date(project.end_date).getTime() - Date.now()) / 86_400_000))
    : null;
  const updates = project.updates || [];
  const rewards = project.rewards || [];

  const handleDonate = () => {
    setDonateAmount("");
    setShowDonate(true);
  };

  const pickTier = (t) => {
    setActiveTab("story");
    setDonateAmount(String(t.amount));
    setShowDonate(true);
  };

  const handleRate = async (value) => {
    try {
      await rateProject(project.id, value);
      notifySuccess("تم تسجيل تقييمك.");
      load();
    } catch {
      notifyError("مقدرناش نسجّل التقييم.");
    }
  };

  const handleCancel = async () => {
    setCancelError("");
    try {
      await cancelProject(project.id);
      setConfirmingCancel(false);
      notifySuccess("تم إلغاء المشروع.");
      load();
    } catch (err) {
      setCancelError(err.response?.data?.detail || "مقدرناش نلغي المشروع دلوقتي.");
    }
  };

  const handleReport = async (e) => {
    e.preventDefault();
    if (!reportReason.trim()) return;
    try {
      await reportContent({ project: project.id, reason: reportReason.trim() });
      setReporting(false);
      setReportReason("");
      notifySuccess("تم إرسال البلاغ، شكرًا لك.");
    } catch {
      notifyError("مقدرناش نرسل البلاغ، حاول تاني.");
    }
  };

  const handlePostUpdate = async (e) => {
    e.preventDefault();
    if (!updateTitle.trim() || !updateBody.trim()) {
      notifyError("اكتب عنوان ووصف التحديث.");
      return;
    }
    setPostingUpdate(true);
    try {
      await addProjectUpdate(project.id, { title: updateTitle.trim(), body: updateBody.trim() });
      notifySuccess("تم نشر التحديث.");
      setUpdateTitle("");
      setUpdateBody("");
      load();
    } catch {
      notifyError("مقدرناش ننشر التحديث.");
    } finally {
      setPostingUpdate(false);
    }
  };

  const handlePostTier = async (e) => {
    e.preventDefault();
    const value = Number(tierAmount);
    if (!tierTitle.trim() || !value || value <= 0) {
      notifyError("اكتب عنوان ومبلغ صحيح للمستوى.");
      return;
    }
    setPostingTier(true);
    try {
      await addRewardTier(project.id, {
        title: tierTitle.trim(),
        description: tierDesc.trim() || tierTitle.trim(),
        amount: value.toFixed(2),
      });
      notifySuccess("تم إضافة مستوى المكافأة.");
      setTierTitle("");
      setTierDesc("");
      setTierAmount("");
      load();
    } catch {
      notifyError("مقدرناش نضيف المستوى.");
    } finally {
      setPostingTier(false);
    }
  };

  const tabs = [
    { key: "story", label: "قصة المشروع", icon: BookOpen, badge: null },
    { key: "updates", label: "التحديثات", icon: History, badge: updates.length },
    { key: "rewards", label: "مستويات الدعم", icon: Gift, badge: rewards.length },
  ];

  return (
    <div className="page">
      <div className="detail-grid">
        <div>
          <div className="gallery-main">
            {images.length ? (
              <img src={images[activeImage].image} alt={project.title} />
            ) : (
              "لا توجد صورة"
            )}
          </div>
          {images.length > 1 && (
            <div className="gallery-thumbs">
              {images.map((img, i) => (
                <button
                  key={img.id}
                  className={i === activeImage ? "active" : ""}
                  onClick={() => setActiveImage(i)}
                >
                  <img src={img.image} alt="" />
                </button>
              ))}
            </div>
          )}

          <div className="detail-meta-row">
            {project.category && <span className="catp">{project.category.name}</span>}
            <StatusBadge status={project.status} />
            {daysLeft !== null && daysLeft !== undefined && (
              <span className="days-left">
                <CalendarDays size={14} />
                متبقي <bdi>{daysLeft}</bdi> يوم
              </span>
            )}
            <span>
              {project.creator.first_name} {project.creator.last_name}
            </span>
          </div>
          <h1 className="detail-title">{project.title}</h1>

          {project.average_rating != null && (
            <div className="rating-row" style={{ marginTop: 0 }}>
              <StarRating value={project.average_rating} disabled />
              <span style={{ fontSize: "0.82rem", color: "var(--ink-600)" }}>
                ({project.rating_count})
              </span>
            </div>
          )}

          <div className="tabs" role="tablist">
            {tabs.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={activeTab === t.key}
                className={`tab-btn${activeTab === t.key ? " active" : ""}`}
                onClick={() => setActiveTab(t.key)}
              >
                <t.icon size={16} style={{ verticalAlign: "middle", marginInlineEnd: 6 }} />
                {t.label}
                {t.badge ? <span className="tab-count">{t.badge}</span> : null}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              className="gen-tab"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              {activeTab === "story" && (
                <>
                  <p className="detail-body">{project.details}</p>
                  {project.tags?.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      {project.tags.map((t) => (
                        <span key={t.id} className="tag-chip">
                          #{t.name}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}

              {activeTab === "updates" && (
                updates.length ? (
                  <div className="updates-timeline">
                    {updates.map((u) => (
                      <div key={u.id} className="update-item">
                        <h4>{u.title}</h4>
                        <div className="update-meta">
                          {new Date(u.created_at).toLocaleDateString("ar-EG", { year: "numeric", month: "long", day: "numeric" })}
                        </div>
                        {u.image_url && (
                          <img src={u.image_url} alt="" style={{ borderRadius: 12, margin: "8px 0", maxHeight: 260, objectFit: "cover" }} />
                        )}
                        <p>{u.body}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">لسه مفيش تحديثات من صاحب المشروع.</p>
                )
              )}

              {activeTab === "rewards" && (
                rewards.length ? (
                  <div className="rewards-grid">
                    {rewards.map((r, i) => (
                      <button
                        key={r.id}
                        className={`reward-card${String(r.amount) === String(Number(amount)) ? " selected" : ""}`}
                        onClick={() => pickTier(r)}
                        style={{}}
                      >
                        <span className="reward-amount">
                          <bdi>{Number(r.amount).toLocaleString("en-US")}</bdi> ج.م
                        </span>
                        <h4>{r.title}</h4>
                        <p>{r.description}</p>
                        <span className="reward-meta">
                          <span>
                            {r.quantity != null
                              ? `متبقي ${Math.max(0, r.quantity)} مكان`
                              : "عدد غير محدود"}
                          </span>
                          <span>{r.estimated_delivery}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">لسه مفيش مستويات دعم مضافة.</p>
                )
              )}
            </motion.div>
          </AnimatePresence>

          {isCreator && (
            <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
              <button className="btn btn-outline" onClick={() => navigate(`/projects/${project.id}/edit`)}>
                تعديل المشروع
              </button>
              {canCancel && !confirmingCancel && (
                <button className="btn btn-outline" onClick={() => setConfirmingCancel(true)}>
                  إلغاء المشروع
                </button>
              )}
              {confirmingCancel && (
                <>
                  <button className="btn btn-primary" onClick={handleCancel}>
                    متأكد؟ إلغاء نهائي
                  </button>
                  <button className="btn btn-ghost" style={{ color: "var(--ink-600)" }} onClick={() => setConfirmingCancel(false)}>
                    تراجع
                  </button>
                </>
              )}
            </div>
          )}
          {cancelError && <div className="form-alert" style={{ marginTop: 14 }}>{cancelError}</div>}

          {isCreator && (
            <>
              <details className="panel-card">
                <summary>إضافة تحديث جديد</summary>
                <div className="field">
                  <label>العنوان</label>
                  <input className="input" value={updateTitle} onChange={(e) => setUpdateTitle(e.target.value)} placeholder="مثال: خطوة جديدة في التنفيذ" />
                </div>
                <div className="field">
                  <label>التفاصيل</label>
                  <textarea className="input" rows={4} value={updateBody} onChange={(e) => setUpdateBody(e.target.value)} placeholder="اكتب التحديث بالتفصيل..." />
                </div>
                <button className="btn btn-primary" disabled={postingUpdate} onClick={handlePostUpdate}>
                  {postingUpdate ? "بيتم النشر..." : "نشر التحديث"}
                </button>
              </details>

              <details className="panel-card">
                <summary>إضافة مستوى دعم</summary>
                <div className="field">
                  <label>العنوان</label>
                  <input className="input" value={tierTitle} onChange={(e) => setTierTitle(e.target.value)} placeholder="مثال: بطاقة شكر خاصة" />
                </div>
                <div className="field">
                  <label>الوصف</label>
                  <textarea className="input" rows={3} value={tierDesc} onChange={(e) => setTierDesc(e.target.value)} placeholder="الوصف التفصيلي للمستوى..." />
                </div>
                <div className="field">
                  <label>المبلغ (ج.م)</label>
                  <input type="number" min="1" className="input" value={tierAmount} onChange={(e) => setTierAmount(e.target.value)} />
                </div>
                <button className="btn btn-primary" disabled={postingTier} onClick={handlePostTier}>
                  {postingTier ? "بيتم الإضافة..." : "إضافة المستوى"}
                </button>
              </details>
            </>
          )}

          {!isCreator && user && (
            <div style={{ marginTop: 22 }}>
              {!reporting ? (
                <button className="comment-actions" style={{ background: "none", border: "none", color: "var(--danger)", cursor: "pointer", fontSize: "0.82rem", alignItems: "center", display: "inline-flex", gap: 6 }} onClick={() => setReporting(true)}>
                  <Flag size={14} />
                  الإبلاغ عن هذا المشروع
                </button>
              ) : (
                <form className="reply-form" onSubmit={handleReport}>
                  <input className="input" placeholder="سبب الإبلاغ..." value={reportReason} onChange={(e) => setReportReason(e.target.value)} autoFocus />
                  <button className="btn btn-outline">إرسال</button>
                </form>
              )}
            </div>
          )}

          {project.similar_projects?.length > 0 && (
            <div className="section" style={{ paddingInline: 0 }}>
              <h2 className="section-heading">مشاريع مشابهة</h2>
              <div className="similar-grid">
                {project.similar_projects.map((p) => (
                  <ProjectCard key={p.id} project={p} />
                ))}
              </div>
            </div>
          )}

          <CommentsSection projectId={project.id} />
        </div>

        <aside className="donate-card">
          <div className="raised">
            <bdi>{raised.toLocaleString("ar-EG")}</bdi> ج.م
          </div>
          <div className="target">
            من هدف <bdi>{target.toLocaleString("ar-EG")}</bdi> ج.م — <bdi>{pct}%</bdi>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="progress-note">
            {updates.length ? (
              <>
                <History size={12} style={{ verticalAlign: "middle", marginInlineEnd: 4 }} />
                {updates.length} تحديث {updates.length > 1 ? "حتى الآن" : "واحد"}
              </>
            ) : null}
          </div>

          {canDonate && (
            <button className="btn btn-primary btn-block" style={{ marginTop: 18 }} onClick={handleDonate}>
              تبرع الآن
            </button>
          )}

          {!user && (
            <Link to="/login" className="btn btn-primary btn-block" style={{ marginTop: 18 }}>
              سجّل دخول للتبرع
            </Link>
          )}

          {user && isCreator && (
            <p style={{ marginTop: 18, fontSize: "0.82rem", color: "var(--ink-600)" }}>
              دي حملتك — مينفعش تتبرع لمشروعك.
            </p>
          )}

          {user && !isCreator && project.status !== "running" && (
            <p style={{ marginTop: 18, fontSize: "0.82rem", color: "var(--ink-600)" }}>
              الحملة دي مش بتستقبل تبرعات دلوقتي.
            </p>
          )}

          {user && (
            <div style={{ marginTop: 20 }}>
              <p style={{ fontSize: "0.82rem", fontWeight: 600, marginBottom: 6 }}>قيّم المشروع</p>
              <StarRating value={project.my_rating || 0} onRate={handleRate} />
            </div>
          )}

          <div className="stats-row">
            <span>
              يبدأ <bdi>{formatDate(project.start_date)}</bdi>
            </span>
            <span>
              ينتهي <bdi>{formatDate(project.end_date)}</bdi>
            </span>
          </div>
        </aside>
      </div>

      <DonationModal
        open={showDonate}
        onClose={() => setShowDonate(false)}
        projectId={project.id}
        projectTitle={project.title}
        initialAmount={donateAmount ? Number(donateAmount) : null}
        onSuccess={load}
      />
    </div>
  );
}