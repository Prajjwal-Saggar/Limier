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
      {lowPct > 0 && <div style={{ width: `${lowPct}%` }} className="bg-risk-low transition-all duration-1000" />}
      {medPct > 0 && <div style={{ width: `${medPct}%` }} className="bg-risk-medium transition-all duration-1000" />}
      {highPct > 0 && <div style={{ width: `${highPct}%` }} className="bg-risk-high transition-all duration-1000" />}
    </div>
  );
}
