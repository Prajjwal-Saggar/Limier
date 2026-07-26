interface StatBarProps {
  low?: number;
  medium?: number;
  high?: number;
  total?: number;
  className?: string;
}

export function StatBar({ low = 0, medium = 0, high = 0, total, className = "" }: StatBarProps) {
  const sum = total || (low + medium + high);
  if (sum === 0) return <div className={`h-2 w-full bg-muted rounded-full ${className}`} />;

  const lowPct = (low / sum) * 100;
  const medPct = (medium / sum) * 100;
  const highPct = (high / sum) * 100;

  return (
    <div className={`flex h-2 w-full overflow-hidden rounded-full bg-muted ${className}`}>
      {lowPct > 0 && <div style={{ width: `${lowPct}%` }} className="bg-risk-low transition-all duration-1000 flex items-center justify-center text-[10px] font-bold text-black/80">{lowPct > 5 ? `${lowPct.toFixed(0)}%` : ''}</div>}
      {medPct > 0 && <div style={{ width: `${medPct}%` }} className="bg-risk-medium transition-all duration-1000 flex items-center justify-center text-[10px] font-bold text-black/80">{medPct > 5 ? `${medPct.toFixed(0)}%` : ''}</div>}
      {highPct > 0 && <div style={{ width: `${highPct}%` }} className="bg-risk-high transition-all duration-1000 flex items-center justify-center text-[10px] font-bold text-black/80">{highPct > 5 ? `${highPct.toFixed(0)}%` : ''}</div>}
    </div>
  );
}
