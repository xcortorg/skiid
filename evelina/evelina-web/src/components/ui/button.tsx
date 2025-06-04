import React, { ButtonHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', children, ...props }, ref) => {
    const variantStyles = {
      default: 'bg-theme hover:bg-theme/90 text-white',
      destructive: 'bg-red-500 hover:bg-red-600 text-white',
      outline: 'border border-theme text-theme hover:bg-theme/10',
      secondary: 'bg-[#222] hover:bg-[#333] text-white',
      ghost: 'hover:bg-[#222] text-gray-300 hover:text-white',
      link: 'text-theme underline-offset-4 hover:underline',
    };

    const sizeStyles = {
      default: 'py-2 px-4 text-sm',
      sm: 'py-1 px-3 text-xs',
      lg: 'py-3 px-6 text-base',
    };

    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-theme/20 disabled:opacity-50 disabled:pointer-events-none',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button'; 