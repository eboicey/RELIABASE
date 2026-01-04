export function Spinner() {
  return (
    <div className="inline-flex items-center gap-2 text-slate-300 text-sm">
      <span className="h-2 w-2 rounded-full bg-accent-400 animate-ping" />
      <span>Loading...</span>
    </div>
  );
}
