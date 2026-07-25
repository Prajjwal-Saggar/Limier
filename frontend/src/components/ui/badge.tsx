import * as React from "react"
import { cn } from "./button"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "low" | "medium" | "high"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "border-transparent bg-primary text-black shadow-[0_0_10px_rgba(34,197,94,0.3)]",
    secondary: "border-transparent bg-muted text-foreground",
    destructive: "border-transparent bg-red-900/40 text-red-400",
    outline: "text-foreground border-border",
    low: "border-transparent bg-risk-low/20 text-risk-low border border-risk-low/30 shadow-[0_0_8px_rgba(34,197,94,0.15)]",
    medium: "border-transparent bg-risk-medium/20 text-risk-medium border border-risk-medium/30 shadow-[0_0_8px_rgba(245,158,11,0.15)]",
    high: "border-transparent bg-risk-high/20 text-risk-high border border-risk-high/30 shadow-[0_0_8px_rgba(239,68,68,0.15)]",
  }

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )}
      {...props}
    />
  )
}

export { Badge }
