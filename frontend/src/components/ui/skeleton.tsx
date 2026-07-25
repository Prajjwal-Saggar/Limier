import { cn } from "./button"

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted/80 relative overflow-hidden", className)}
      {...props}
    >
      <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-primary/10 to-transparent animate-[shimmer_2s_infinite]" />
    </div>
  )
}

export { Skeleton }
