import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { initials } from "../constants";

function CommentNode({ comment, childrenOf, depth, ctx }) {
  const { currentUser, isAdmin, canComment, reload, setError } = ctx;
  const [replying, setReplying] = useState(false);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const isMine = comment.author.id === currentUser.id;
  const replies = childrenOf[comment.id] || [];

  async function submitReply(event) {
    event.preventDefault();
    try {
      await api.post(`/tickets/${comment.ticket_id}/comments`, { body: text, parent_id: comment.id });
      setText("");
      setReplying(false);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function submitEdit(event) {
    event.preventDefault();
    try {
      await api.patch(`/comments/${comment.id}`, { body: text });
      setEditing(false);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove() {
    if (!window.confirm("Delete this comment and all replies to it?")) return;
    try {
      await api.delete(`/comments/${comment.id}`);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <li className={depth > 0 ? "ml-5 border-l border-line pl-4" : ""}>
      <div className="flex gap-3">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink font-mono text-xs text-paper">
          {initials(comment.author.full_name)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm">
            <span className="font-semibold">{comment.author.full_name}</span>
            <span className="ml-2 text-xs text-muted">{new Date(comment.created_at).toLocaleString()}</span>
          </p>
          {editing ? (
            <form onSubmit={submitEdit} className="mt-1 space-y-2">
              <textarea required rows={3} maxLength={5000} className="input" value={text} onChange={(e) => setText(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn btn-primary">Save</button>
                <button type="button" className="btn" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </form>
          ) : (
            // React escapes this text, so user content can never run as HTML.
            <p className="mt-0.5 whitespace-pre-wrap break-words text-sm">{comment.body}</p>
          )}
          {!editing && (
            <div className="mt-1 flex gap-3 text-xs text-muted">
              {canComment && (
                <button className="hover:text-ink" onClick={() => { setText(""); setReplying(!replying); }}>
                  Reply
                </button>
              )}
              {canComment && isMine && (
                <button className="hover:text-ink" onClick={() => { setText(comment.body); setEditing(true); }}>
                  Edit
                </button>
              )}
              {(isMine || isAdmin) && (
                <button className="hover:text-red-700" onClick={remove}>Delete</button>
              )}
            </div>
          )}
          {replying && (
            <form onSubmit={submitReply} className="mt-2 space-y-2">
              <textarea required autoFocus rows={2} maxLength={5000} className="input" placeholder="Write a reply…" value={text} onChange={(e) => setText(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn btn-primary">Reply</button>
                <button type="button" className="btn" onClick={() => setReplying(false)}>Cancel</button>
              </div>
            </form>
          )}
        </div>
      </div>
      {replies.length > 0 && (
        <ul className="mt-3 space-y-3">
          {replies.map((reply) => (
            <CommentNode key={reply.id} comment={reply} childrenOf={childrenOf} depth={depth + 1} ctx={ctx} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function Comments({ ticketId, canComment, currentUser, isAdmin }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [text, setText] = useState("");

  const reload = useCallback(async () => {
    try {
      const { data } = await api.get(`/tickets/${ticketId}/comments`);
      setComments(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleAdd(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post(`/tickets/${ticketId}/comments`, { body: text });
      setText("");
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  // Group replies under their parent so the thread can be drawn as a tree.
  const childrenOf = {};
  const roots = [];
  for (const comment of comments) {
    if (comment.parent_id === null) roots.push(comment);
    else (childrenOf[comment.parent_id] ||= []).push(comment);
  }
  const ctx = { currentUser, isAdmin, canComment, reload, setError };

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
        Comments <span className="font-mono">{comments.length}</span>
      </h3>
      {loading ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : roots.length === 0 ? (
        <p className="text-sm text-muted">No comments yet.</p>
      ) : (
        <ul className="space-y-4">
          {roots.map((comment) => (
            <CommentNode key={comment.id} comment={comment} childrenOf={childrenOf} depth={0} ctx={ctx} />
          ))}
        </ul>
      )}
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      {canComment && (
        <form onSubmit={handleAdd} className="mt-4 space-y-2">
          <textarea required rows={3} maxLength={5000} className="input" placeholder="Add a comment…" value={text} onChange={(e) => setText(e.target.value)} />
          <button className="btn btn-primary">Comment</button>
        </form>
      )}
    </section>
  );
}
