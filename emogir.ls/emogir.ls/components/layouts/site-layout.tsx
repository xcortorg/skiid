interface SiteLayoutProps {
  children: React.ReactNode;
  variant?: "landing" | "default" | "dashboard";
}

export default function SiteLayout({
  children,
  variant = "default",
}: SiteLayoutProps) {
  return (
    <div
      className={`min-h-screen w-full relative ${
        variant === "landing"
          ? "animated-bg fade-in"
          : variant === "default"
            ? "animated-bg"
            : "bg-darker"
      }`}
    >
      {children}
    </div>
  );
}
