import { useEffect, useState } from "react";
import { listProjects } from "../api/projects";
import ProjectCard from "../components/ProjectCard";
import Pagination from "../components/Pagination";

export default function ProjectList() {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(false);
    listProjects(page)
      .then(({ data }) => setResult(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [page, retry]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>All Projects</h1>
      </div>

      {error && (
        <div className="err-state">
          <h3>We couldn't load the projects</h3>
          <p>There was a connection problem. Please try again later.</p>
          <button className="btn btn-outline" onClick={() => setRetry((r) => r + 1)}>
            Try Again
          </button>
        </div>
      )}
      {loading && (
        <div className="skeleton-grid">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="skeleton-card">
              <div className="skeleton sk-img" />
              <div className="sk-body">
                <div className="skeleton sk-line" />
                <div className="skeleton sk-line short" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && result && (
        <>
          {result.results.length ? (
            <div className="project-grid">
              {result.results.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </div>
          ) : (
            <p className="empty-state">No projects available yet.</p>
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