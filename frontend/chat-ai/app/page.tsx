'use client';

import { useEffect, useRef, useState } from 'react';

type UploadedMeta = {
  original_name: string;
  stored_name: string;
  bytes: number;
  sha256: string;
  content_type: string;
};

export default function Home() {
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

  // health
  const [health, setHealth] = useState('unknown');

  // uploads
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [picked, setPicked] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadedMeta[]>([]);
  const [error, setError] = useState<string | null>(null);

  // chat
  const [chatInput, setChatInput] = useState('');
  const [chatAnswer, setChatAnswer] = useState('');

  // ---- health check ----
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${api}/health`);
        const j = await r.json();
        setHealth(j.status ?? 'unknown');
      } catch {
        setHealth('down');
      }
    })();
  }, [api]);

  // ---- file picking helpers ----
  function onPickClick() {
    fileInputRef.current?.click();
  }
  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : [];
    setFiles(e.target.files);
    setPicked(list);
  }

  // ---- presign helper ----
  async function presignOne(file: File) {
    const r = await fetch(`${api}/upload/presign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
      }),
    });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`presign failed: ${r.status} ${t}`);
    }
    return r.json() as Promise<{ url: string; fields: Record<string, string>; key: string }>;
  }

  // ---- upload to S3 via presigned POST ----
  async function onUpload() {
    setError(null);
    setResult([]);

    if (!files || files.length === 0) {
      setError('Pick at least one file.');
      return;
    }

    setUploading(true);
    try {
      const uploaded: UploadedMeta[] = [];

      for (const f of Array.from(files)) {
        // 1) get presigned POST from backend
        const { url, fields, key } = await presignOne(f);

        // 2) POST to S3 directly
        const form = new FormData();

        // add all returned fields exactly
        Object.entries(fields).forEach(([k, v]) => form.append(k, v as string));

        // only add Content-Type if presign didn't include it
        if (!('Content-Type' in fields)) {
          form.append('Content-Type', f.type || 'application/octet-stream');
        }

        // finally the file
        form.append('file', f);

        const s3Resp = await fetch(url, { method: 'POST', body: form });
        if (!s3Resp.ok) {
          const txt = await s3Resp.text(); // S3 returns XML with exact error
          throw new Error(`S3 upload failed: ${s3Resp.status} ${txt}`);
        }

        uploaded.push({
          original_name: f.name,
          stored_name: key.split('/').pop() || f.name,
          bytes: f.size,
          sha256: 's3-presigned', // placeholder; compute server-side later if needed
          content_type: f.type || 'application/octet-stream',
        });
      }

      setResult(uploaded);
      // clear picker after success
      setFiles(null);
      setPicked([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (e: any) {
      setError(e.message ?? 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  // ---- chat ----
  async function onChat() {
    setChatAnswer('');
    if (!chatInput.trim()) return;
    try {
      const resp = await fetch(`${api}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: chatInput }),
      });
      if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
      const json = await resp.json(); // { answer, citations }
      setChatAnswer(json.answer ?? '(no answer)');
    } catch (e: any) {
      setChatAnswer(`Error: ${e.message ?? 'failed'}`);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Mavik Chat Assistant (MVP shell)</h1>
        <p className="mt-2">API health: <b>{health}</b></p>
      </header>

      {/* Upload Section */}
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Upload documents (S3 mode)</h2>

        <input
          ref={fileInputRef}
          id="files"
          type="file"
          multiple
          className="hidden"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv"
          onChange={onFileChange}
        />

        <div className="flex items-center gap-3">
          <button type="button" className="border rounded px-3 py-1" onClick={onPickClick}>
            Choose files
          </button>
          <button className="border rounded px-3 py-1" onClick={onUpload} disabled={uploading}>
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>

        {picked.length > 0 ? (
          <ul className="list-disc ml-6">
            {picked.map((f, i) => (
              <li key={i}>{f.name} ({f.size} bytes)</li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400">No files chosen yet.</p>
        )}

        {error && <p className="text-red-600">{error}</p>}

        {result.length > 0 && (
          <>
            <h3 className="font-medium mt-2">Uploaded</h3>
            <ul className="list-disc ml-6">
              {result.map((m, i) => (
                <li key={i}>
                  {m.original_name} → {m.stored_name} ({m.bytes} bytes) — {m.sha256.slice(0, 12)}…
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* Chat Section */}
      <section className="space-y-3">
        <h2 className="text-lg font-medium">Chat</h2>
        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Ask a question…"
          className="p-2 border rounded w-full"
        />
        <button className="border rounded px-3 py-1" onClick={onChat}>
          Send
        </button>
        {chatAnswer && <p className="mt-2">Answer: {chatAnswer}</p>}
      </section>
    </main>
  );
}
