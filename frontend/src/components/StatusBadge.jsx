const LABELS = {
  running: "Running",
  ended: "Ended",
  cancelled: "Cancelled",
};

export default function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{LABELS[status] || status}</span>;
}
