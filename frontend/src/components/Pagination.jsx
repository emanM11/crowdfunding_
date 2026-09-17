export default function Pagination({ page, setPage, hasNext, hasPrevious, loading }) {
  if (!hasNext && !hasPrevious && page === 1) return null;
  return (
    <div className="pagination">
      <button
        className="btn btn-outline"
        disabled={!hasPrevious || loading}
        onClick={() => setPage((p) => Math.max(1, p - 1))}
      >
        Previous
      </button>
      <span>Page {page}</span>
      <button
        className="btn btn-outline"
        disabled={!hasNext || loading}
        onClick={() => setPage((p) => p + 1)}
      >
        Next
      </button>
    </div>
  );
}
