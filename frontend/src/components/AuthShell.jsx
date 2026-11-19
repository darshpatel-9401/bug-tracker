export default function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded bg-signal font-mono text-white">#</span>
          <span className="text-xl font-semibold tracking-tight">Bugtracker</span>
        </div>
        <div className="panel p-6">
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="mb-5 mt-1 text-sm text-muted">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  );
}
