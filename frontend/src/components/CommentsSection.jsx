import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { addComment, listComments, replyToComment, reportContent } from "../api/core";
import { useAuth } from "../context/AuthContext";

const MAX_COMMENT_LENGTH = 1000;

export default function CommentsSection({ projectId }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState("");
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    listComments(projectId)
      .then(({ data }) => setComments(data.results))
      .finally(() => setLoading(false));
  };

  useEffect(load, [projectId]);

  const handlePost = async (e) => {
    e.preventDefault();
    const text = newComment.trim();
    if (!text) return;
    setError("");
    setPosting(true);
    try {
      await addComment(projectId, text);
      setNewComment("");
      load();
    } catch {
      setError("We couldn't post the comment right now.");
    } finally {
      setPosting(false);
    }
  };

  return (
    <section className="section" style={{ paddingBottom: 0 }}>
      <h2 className="section-heading">Comments</h2>

      {user ? (
        <form onSubmit={handlePost} className="field" style={{ display: "flex", gap: 10 }}>
          <input
            className="input"
            placeholder="Write a comment..."
            value={newComment}
            maxLength={MAX_COMMENT_LENGTH}
            onChange={(e) => setNewComment(e.target.value)}
          />
          <button className="btn btn-primary" disabled={posting || !newComment.trim()}>
            Post
          </button>
        </form>
      ) : (
        <p className="empty-state">
          <Link to="/login">Log In</Link> to leave a comment.
        </p>
      )}

      {error && <div className="form-alert">{error}</div>}
      {loading && <p className="empty-state">Loading...</p>}

      {!loading &&
        (comments.length ? (
          <div>
            {comments.map((c) => (
              <CommentItem key={c.id} comment={c} projectId={projectId} onChanged={load} isAuthed={Boolean(user)} />
            ))}
          </div>
        ) : (
          <p className="empty-state">No comments yet — be the first to comment.</p>
        ))}
    </section>
  );
}

function CommentItem({ comment, onChanged, isAuthed }) {
  const [replying, setReplying] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [reportSent, setReportSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submitReply = async (e) => {
    e.preventDefault();
    const text = replyText.trim();
    if (!text) return;
    setBusy(true);
    try {
      await replyToComment(comment.id, text);
      setReplying(false);
      setReplyText("");
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const submitReport = async (e) => {
    e.preventDefault();
    const reason = reportReason.trim();
    if (!reason) return;
    setBusy(true);
    try {
      await reportContent({ comment: comment.id, reason });
      setReporting(false);
      setReportReason("");
      setReportSent(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="comment">
      <span className="author">
        {comment.user.first_name} {comment.user.last_name}
      </span>
      <span className="date"><bdi>{new Date(comment.created_at).toLocaleDateString("ar-EG")}</bdi></span>
      <p className="text">{comment.text}</p>

      {isAuthed && (
        <div className="comment-actions">
          <button onClick={() => setReplying((v) => !v)}>Reply</button>
          {reportSent ? (
            <span style={{ color: "var(--success)" }}>Reported</span>
          ) : (
            <button className="danger" onClick={() => setReporting((v) => !v)}>
              Report
            </button>
          )}
        </div>
      )}

      {replying && (
        <form className="reply-form" onSubmit={submitReply}>
          <input
            className="input"
            placeholder="Write your reply..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            autoFocus
          />
          <button className="btn btn-outline" disabled={busy || !replyText.trim()}>
            Send
          </button>
        </form>
      )}

      {reporting && (
        <form className="reply-form" onSubmit={submitReport}>
          <input
            className="input"
            placeholder="Reason for reporting..."
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
            autoFocus
          />
          <button className="btn btn-outline" disabled={busy || !reportReason.trim()}>
            Submit Report
          </button>
        </form>
      )}

      {comment.replies?.map((r) => (
        <ReplyRow key={r.id} reply={r} isAuthed={isAuthed} />
      ))}
    </div>
  );
}

function ReplyRow({ reply, isAuthed }) {
  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const submitReport = async (e) => {
    e.preventDefault();
    const reason = reportReason.trim();
    if (!reason) return;
    setBusy(true);
    try {
      await reportContent({ comment: reply.id, reason });
      setReporting(false);
      setReportReason("");
      setSent(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="reply">
      <span className="author">
        {reply.user.first_name} {reply.user.last_name}
      </span>
      <span className="date">
        <bdi>{new Date(reply.created_at).toLocaleDateString("ar-EG")}</bdi>
      </span>
      <p className="text">{reply.text}</p>

      {isAuthed && !sent && (
        <div className="comment-actions">
          <button className="danger" onClick={() => setReporting((v) => !v)}>
            Report
          </button>
        </div>
      )}
      {sent && <p style={{ fontSize: "0.76rem", color: "var(--success)" }}>Reported.</p>}

      {reporting && (
        <form className="reply-form" onSubmit={submitReport}>
          <input
            className="input"
            placeholder="Reason for reporting..."
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
            autoFocus
          />
          <button className="btn btn-outline" disabled={busy || !reportReason.trim()}>
            Submit Report
          </button>
        </form>
      )}
    </div>
  );
}
