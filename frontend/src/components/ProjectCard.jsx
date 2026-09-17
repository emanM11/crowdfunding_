import { Link } from "react-router-dom";

function daysLeft(endDate) {
  if (!endDate) return null;
  const end = new Date(endDate).getTime();
  if (Number.isNaN(end)) return null;
  return Math.max(0, Math.ceil((end - Date.now()) / 86_400_000));
}

export default function ProjectCard({ project }) {
  const target = Number(project.total_target) || 0;
  const raised = Number(project.total_donations) || 0;
  const pct = target > 0 ? Math.min(100, Math.round((raised / target) * 100)) : 0;
  const ended = project.status === "ended" || project.status === "cancelled";
  const days = project.status === "running" ? daysLeft(project.end_date) : null;

  return (
    <Link to={`/projects/${project.id}`} className="project-card">
      <div className="thumb">
        {project.thumbnail ? (
          <img src={project.thumbnail} alt={project.title} loading="lazy" />
        ) : (
          "No Image Available"
        )}
        <div className="badges">
          {project.category ? (
            <span className="cat">{project.category.name}</span>
          ) : (
            <span />
          )}
          {project.is_featured && <span className="featured-chip">Featured</span>}
          {ended && <span className="ended-chip">Contributions Ended</span>}
        </div>
      </div>
      <div className="body">
        <h3>{project.title}</h3>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="meta">
          <span>
            <bdi>{raised.toLocaleString("en-US")}</bdi> EGP
          </span>
          {days !== null && days !== undefined ? (
            <span>
              <bdi>{days}</bdi> days left
            </span>
          ) : (
            <span className="pct">
              <bdi>{pct}%</bdi>
            </span>
          )}
        </div>
        <span className="cta-link">
          View Project
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </span>
      </div>
    </Link>
  );
}