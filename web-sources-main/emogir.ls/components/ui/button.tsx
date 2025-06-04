import Link from "next/link";
import { IconType } from "react-icons";
import { cn } from "@/lib/utils";

interface ButtonProps {
  text?: string;
  icon?: IconType;
  href?: string;
  className?: string;
  onClick?: (e: React.MouseEvent) => void;
  disabled?: boolean;
  rounded?: boolean;
  type?: "button" | "submit" | "reset";
  loading?: boolean;
  children?: React.ReactNode;
}

export const Button = ({
  text,
  icon: Icon,
  href,
  className,
  onClick,
  disabled,
  rounded = true,
  type = "button",
  loading,
  children,
}: ButtonProps) => {
  const classes = cn(
    "inline-flex items-center gap-2 px-4 h-9 text-sm font-medium transition-all",
    "border border-primary/[0.125] bg-primary/5 bg-gradient-to-br from-primary/[0.01] to-primary/[0.03]",
    "hover:border-primary/20 hover:bg-primary/10 active:bg-primary/15",
    "disabled:opacity-50 disabled:pointer-events-none",
    "focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/20",
    "focus:ring-0 focus:ring-offset-0 outline-none",
    "select-none tap-highlight-transparent",
    rounded ? "rounded-lg" : "rounded-md",
    className,
  );

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children || (loading ? "Loading..." : text && <span>{text}</span>)}
        {Icon && <Icon size={16} className="text-primary" />}
      </Link>
    );
  }

  return (
    <button
      className={classes}
      onClick={onClick}
      disabled={disabled || loading}
      type={type}
    >
      {children || (loading ? "Loading..." : text && <span>{text}</span>)}
      {Icon && <Icon size={16} className="text-primary" />}
    </button>
  );
};
