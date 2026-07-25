import { Badge } from "./ui/badge";

interface RiskBadgeProps {
  level: "low" | "medium" | "high";
  className?: string;
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  return (
    <Badge variant={level} className={`uppercase tracking-wider ${className || ""}`}>
      {level}
    </Badge>
  );
}
