import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { search } from "../api/core";
import ProjectCard from "../components/ProjectCard";
import Pagination from "../components/Pagination";

export default function SearchResults() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setPage(1);
  }, [q]);

  useEffect(() => {
    if (!q.trim()) {
      setResult({ results: [], next: null, previous: null });
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(false);
    search(q, page)
      .then(({ data }) => setResult(data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [q, page, retry]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>نتائج البحث عن "{q}"</h1>
      </div>

      {error && (
        <div className="err-state">
          <h3>مقدرناش نكمل البحث</h3>
          <p>حصلت مشكلة في الاتصال، حاول تاني بعد شوية.</p>
          <button className="btn btn-outline" onClick={() => setRetry((r) => r + 1)}>
            إعادة المحاولة
          </button>
        </div>
      )}
      {loading && <p className="empty-state">بيتم البحث...</p>}

      {!loading && result && (
        <>
          {result.results.length ? (
            <div className="project-grid">
              {result.results.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </div>
          ) : (
            <p className="empty-state">مفيش نتايج مطابقة.</p>
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
