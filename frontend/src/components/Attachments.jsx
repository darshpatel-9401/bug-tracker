import { useCallback, useEffect, useRef, useState } from "react";
import api, { errorMessage } from "../api/client";

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];

// The download route needs our JWT, so <img src> cannot call it directly.
// We fetch the bytes with axios (which adds the token) and show them through a temporary blob URL.
function Thumbnail({ attachment }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    api
      .get(`/attachments/${attachment.id}/download`, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setUrl(objectUrl);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachment.id]);

  if (!url) return <div className="h-24 w-32 animate-pulse rounded bg-stone-200" />;
  return (
    <a href={url} target="_blank" rel="noreferrer">
      <img src={url} alt={attachment.filename} className="h-24 w-32 rounded border border-line object-cover" />
    </a>
  );
}

export default function Attachments({ ticketId, canUpload, currentUser, isAdmin }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const reload = useCallback(async () => {
    try {
      const { data } = await api.get(`/tickets/${ticketId}/attachments`);
      setItems(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [ticketId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    setError("");
    setUploading(true);
    const body = new FormData();
    body.append("file", file);
    try {
      await api.post(`/tickets/${ticketId}/attachments`, body);
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDownload(attachment) {
    try {
      const res = await api.get(`/attachments/${attachment.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = attachment.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(attachment) {
    if (!window.confirm(`Delete ${attachment.filename}?`)) return;
    try {
      await api.delete(`/attachments/${attachment.id}`);
      setItems((current) => current.filter((a) => a.id !== attachment.id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Attachments <span className="font-mono">{items.length}</span>
        </h3>
        {canUpload && (
          <label className="btn cursor-pointer">
            {uploading ? "Uploading…" : "Upload screenshot"}
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.log"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        )}
      </div>
      {error && <p className="mb-2 text-sm text-red-700">{error}</p>}
      {items.length === 0 ? (
        <p className="text-sm text-muted">Nothing attached.</p>
      ) : (
        <ul className="flex flex-wrap gap-3">
          {items.map((a) => (
            <li key={a.id} className="w-32">
              {IMAGE_TYPES.includes(a.content_type) ? (
                <Thumbnail attachment={a} />
              ) : (
                <div className="flex h-24 w-32 items-center justify-center rounded border border-line bg-stone-100 font-mono text-xs text-muted">
                  {a.filename.split(".").pop().toUpperCase()}
                </div>
              )}
              <p className="mt-1 truncate text-xs" title={a.filename}>{a.filename}</p>
              <div className="flex gap-2 text-xs text-muted">
                <button className="hover:text-ink" onClick={() => handleDownload(a)}>Download</button>
                {(isAdmin || a.uploader_id === currentUser.id) && (
                  <button className="hover:text-red-700" onClick={() => handleDelete(a)}>Delete</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
