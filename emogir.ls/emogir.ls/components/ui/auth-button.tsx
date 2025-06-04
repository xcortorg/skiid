import { Button } from "./button";
import { IconType } from "react-icons";
import { IconLoader2 } from "@tabler/icons-react";
import { cn } from "@/lib/utils";

interface AuthButtonProps {
  text: string;
  icon?: IconType;
  isLoading?: boolean;
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

export function AuthButton({
  text,
  icon: Icon,
  isLoading = false,
  type = "submit",
  onClick,
  className,
  disabled = false,
}: AuthButtonProps) {
  return (
    <Button
      type={type}
      onClick={onClick}
      disabled={isLoading || disabled}
      className={cn(
        "w-full relative flex items-center justify-center",
        className,
      )}
    >
      <span
        className={cn("flex items-center justify-center gap-2", {
          invisible: isLoading,
        })}
      >
        {Icon && <Icon size={16} />}
        {text}
      </span>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <IconLoader2 size={16} className="animate-spin" />
        </div>
      )}
    </Button>
  );
}
