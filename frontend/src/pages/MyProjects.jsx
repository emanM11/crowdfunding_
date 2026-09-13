import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cancelProject, myProjects } from "../api/projects";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import Reveal from "../components/Reveal";
import { notifySuccess } from "../lib/toast";

const RAISE_COLOR = "#0d9488";
const TARGET_COLOR = "#0ea5e9";

export default function MyProjects() {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmingId, setConfirmingId] = useState(null);
  const [cancelError, setCancelError] = useState("");

  const load = () => {
    setLoading(true);
    myProjects(page)
      .then(({ data }) => setResult(data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [page]);

  const handleCancel = async (id) => {
    setCancelError("");
    try {
      await cancelProject(id);
      setConfirmingId(null);
      notifySuccess("تم إلغاء المشروع.");
      load();
    } catch (err) {
      setCancelError(err.response?.data?.detail || "مقدرناش نلغي المشروع دلوقتي.");
    }
  };

  const projects = result?.results || [];
  const stats = projects.reduce(
    (acc, p) => {
      const target = Number(p.total_target) || 0;
      const raised = Number(p.total_donations) || 0;
      acc.raised += raised;
      acc.target += target;
      acc.active += p.status === "running" ? 1 : 0;
      acc.pct += target > 0 ? (raised / target) * 100 : 0;
      return acc;
    },
    { raised: 0, target: 0, active: 0, pct: 0 }
  );
  const avgPct = projects.length ? Math.round(stats.pct / projects.length) : 0;

  const chartData = projects.slice(0, 9).map((p) => ({
    name: p.title.length > 14 ? `${p.title.slice(0, 14)}…` : p.title,
    "تم جمعه": Number(p.total_donations) || 0,
    "الهدف": Number(p.total_target) || 0,
  }));

  return (
    <div className="page">
      <div className="page-header">
        <h1>مشاريعي</h1>
        <Link to="/projects/new" className="btn btn-primary">
          ابدأ حملة جديدة
        </Link>
      </div>

      {cancelError && <div className="form-alert">{cancelError}</div>}

      {!loading && projects.length > 0 && (
        <>
          <Reveal className="dash-grid">
            <div className="kpi-card">
              <span className="kpi-label">تم جمعه ({projects.length} مشروع)</span>
              <bdi className="kpi-value">
                {stats.raised.toLocaleString("ar-EG")} ج.م
              </bdi>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">إجمالي الأهداف</span>
              <bdi className="kpi-value">
                {stats.target.toLocaleString("ar-EG")} ج.م
              </bdi>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">حملات نشطة</span>
              <div className="kpi-value">{stats.active}</div>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">متوسط الإنجاز</span>
              <div className="kpi-value">
                <bdi>{avgPct}%</bdi>
              </div>
            </div>
          </Reveal>

          {projects.length > 1 && (
            <Reveal className="panel-card chart-box">
              <h3>التحصيل مقابل الهدف</h3>
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, rgba(100,116,139,0.15))" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "var(--ink-500, #64748b)" }}
                      tickFormatter={(v) => (v.length > 10 ? `${v.slice(0, 10)}…` : v)}
                      interval={0}
                      angle={-14}
                      height={40}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "var(--ink-500, #64748b)" }} width={46} />
                    <Tooltip
                      formatter={(v) => Number(v).toLocaleString("ar-EG")}
                      labelStyle={{ fontSize: 12 }}
                      contentStyle={{
                        background: "var(--surface-card, #fff)",
                        border: "1px solid var(--line, #e2e8f0)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="تم جمعه" fill={RAISE_COLOR} radius={[5, 5, 0, 0]} />
                    <Bar dataKey="الهدف" fill={TARGET_COLOR} radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Reveal>
          )}
        </>
      )}

      {loading && <p className="empty-state">بيتم التحميل...</p>}

      {!loading && result && (
        <>
          {projects.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: projects.length > 1 ? 24 : 0 }}>
              {projects.map((p) => {
                const target = Number(p.total_target) || 0;
                const raised = Number(p.total_donations) || 0;
                const pct = target > 0 ? (raised / target) * 100 : 0;
                const canCancel = p.status === "running" && pct < 25;
                return (
                  <div key={p.id} className="donation-row" style={{ alignItems: "center" }}>
                    <div className="thumb">
                      {p.thumbnail ? <img src={p.thumbnail} alt="" /> : null}
                    </div>
                    <div className="grow">
                      <Link to={`/projects/${p.id}`} style={{ fontWeight: 600, textDecoration: "none" }}>
                        {p.title}
                      </Link>
                      <div className="progress-track" style={{ height: 7, maxWidth: 320, marginTop: 8 }}>
                        <div className="progress-fill" style={{ width: `${Math.min(100, pct)}%` }} />
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "var(--ink-600)", marginTop: 4 }}>
                        <bdi>{raised.toLocaleString("ar-EG")}</bdi> / <bdi>{target.toLocaleString("ar-EG")}</bdi> ج.م
                        {"  "}
                        <StatusBadge status={p.status} />
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <Link to={`/projects/${p.id}/edit`} className="btn btn-outline">
                        تعديل
                      </Link>
                      {canCancel && confirmingId !== p.id && (
                        <button className="btn btn-outline" onClick={() => setConfirmingId(p.id)}>
                          إلغاء
                        </button>
                      )}
                      {canCancel && confirmingId === p.id && (
                        <>
                          <button className="btn btn-primary" onClick={() => handleCancel(p.id)}>
                            تأكيد الإلغاء
                          </button>
                          <button className="btn btn-ghost" style={{ color: "var(--ink-600)" }} onClick={() => setConfirmingId(null)}>
                            تراجع
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-state">لسه معملتش أي مشروع.</p>
          )}
          <Pagination
            page={page}
            setPage={setPage}
            hasNext={Boolean(result.next)}
            hasPrevious={Boolean(result.previous)}
            loading={loading}
          />
        </>
      )}
    </div>
  );
}