export function Card({
  children,
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-white/5 bg-black/20 backdrop-blur-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
