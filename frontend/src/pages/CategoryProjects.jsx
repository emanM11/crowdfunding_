import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { categoryProjects } from "../api/projects";
import ProjectCard from "../components/ProjectCard";
import Pagination from "../components/Pagination";

export default function CategoryProjects() {
  const { slug } = useParams();
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setPage(1);
  }, [slug]);

  useEffect(() => {
    setLoading(true);
    setError(false);
    categoryProjects(slug, page)
      .then(({ data }) => setResult(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [slug, page, retry]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>مشاريع {decodeURIComponent(slug)}</h1>
      </div>

      {error && (
        <div className="err-state">
          <h3>مقدرناش نجيب المشاريع</h3>
          <p>حصلت مشكلة في الاتصال، حاول تاني بعد شوية.</p>
          <button className="btn btn-outline" onClick={() => setRetry((r) => r + 1)}>
            إعادة المحاولة
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
            <p className="empty-state">لسه مفيش مشاريع في الفئة دي.</p>
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
