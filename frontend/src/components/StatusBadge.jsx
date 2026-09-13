const LABELS = {
  running: "شغّال",
  ended: "انتهى",
  cancelled: "اتلغى",
};

export default function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{LABELS[status] || status}</span>;
}
