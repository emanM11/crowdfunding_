import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { myDonations } from "../api/projects";
import Pagination from "../components/Pagination";
import Reveal from "../components/Reveal";

const PIE_COLORS = [
  "#0d9488",
  "#0ea5e9",
  "#f59e0b",
  "#8b5cf6",
  "#ef4444",
  "#84cc16",
  "#ec4899",
  "#64748b",
];

const STATUS_META = {
  successful: { label: "Successful", className: "chip-success" },
  pending: { label: "Pending", className: "chip-pending" },
  failed: { label: "Failed", className: "chip-failed" },
};

const CURRENCY_SYMBOL = { EGP: "EGP", USD: "$" };

export default function MyDonations() {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    myDonations(page)
      .then(({ data }) => setResult(data))
      .finally(() => setLoading(false));
  }, [page]);

  const donations = result?.results || [];
  const successful = donations.filter((d) => d.status === "successful");
  const totalOnPage = successful.reduce((s, d) => s + (Number(d.amount) || 0), 0);
  const largest = successful.reduce((m, d) => Math.max(m, Number(d.amount) || 0), 0);

  const byProject = Object.values(
    successful.reduce((acc, d) => {
      const key = d.project_id;
      if (!acc[key]) {
        acc[key] = { name: d.project_title, value: 0 };
      }
      acc[key].value += Number(d.amount) || 0;
      return acc;
    }, {})
  )
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  return (
    <div className="page">
      <div className="page-header">
        <h1>My Donations</h1>
      </div>

      {loading && <p className="empty-state">Loading...</p>}

      {!loading && result && (
        <>
          {donations.length > 0 && (
            <>
              <Reveal className="dash-grid">
                <div className="kpi-card">
                  <span className="kpi-label">Total on Page (Successful Only)</span>
                  <bdi className="kpi-value">
                    {totalOnPage.toLocaleString("en-EG")} EGP
                  </bdi>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Successful Donations</span>
                  <div className="kpi-value">{successful.length}</div>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Largest Donation</span>
                  <bdi className="kpi-value">
                    {largest.toLocaleString("en-EG")} EGP
                  </bdi>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Average Donation</span>
                  <bdi className="kpi-value">
                    {successful.length
                      ? (totalOnPage / successful.length).toLocaleString("en-EG")
                      : "—"}{" "}
                    EGP
                  </bdi>
                </div>
              </Reveal>

              {byProject.length > 1 && (
                <Reveal className="panel-card chart-box">
                  <h3>My Donations by Project</h3>
                  <div style={{ height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={byProject}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={58}
                          outerRadius={104}
                          paddingAngle={2}
                        >
                          {byProject.map((entry, i) => (
                            <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(v) => `${Number(v).toLocaleString("en-EG")} EGP`}
                          contentStyle={{
                            background: "var(--surface-card, #fff)",
                            border: "1px solid var(--line, #e2e8f0)",
                            borderRadius: 10,
                            fontSize: 12,
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="chart-legend">
                    {byProject.map((entry, i) => (
                      <span key={entry.name}>
                        <i style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        {entry.name.length > 40 ? `${entry.name.slice(0, 40)}…` : entry.name}
                      </span>
                    ))}
                  </div>
                </Reveal>
              )}
            </>
          )}

          {donations.length ? (
            <div style={{ marginTop: 24 }}>
              {donations.map((d, idx) => {
                const status = STATUS_META[d.status] || STATUS_META.pending;
                const symbol = CURRENCY_SYMBOL[d.currency] || "EGP";
                return (
                  <div className="donation-row" key={idx}>
                    <div className="thumb">
                      {d.project_image ? <img src={d.project_image} alt="" /> : null}
                    </div>
                    <div className="grow">
                      <Link to={`/projects/${d.project_id}`} style={{ fontWeight: 600, textDecoration: "none" }}>
                        {d.project_title}
                      </Link>
                      <div className="donation-meta">
                        <bdi>{new Date(d.created_at).toLocaleDateString("en-EG")}</bdi>
                        <span className={`status-chip ${status.className}`}>{status.label}</span>
                        {d.payment_method && (
                          <span className="hint" dir="ltr">
                           Card <bdi>•••• {d.payment_method}</bdi>
                          </span>
                        )}
                        {d.status === "successful" && d.transaction_id && (
                          <span className="hint" dir="ltr">
                            ref: <bdi>{d.transaction_id}</bdi>
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="amount">
                      <bdi>{Number(d.amount).toLocaleString("en-EG")}</bdi> {symbol}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-state">You haven't donated to any project yet.</p>
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