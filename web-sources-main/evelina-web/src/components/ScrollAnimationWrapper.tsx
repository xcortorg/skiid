import React, { ReactNode } from 'react';

interface ScrollAnimationWrapperProps {
  children: ReactNode;
  className?: string;
}

function ScrollAnimationWrapper({ children, className = '' }: ScrollAnimationWrapperProps) {
  return (
    <div className={`scroll-animate ${className}`}>
      {children}
    </div>
  );
}

export default ScrollAnimationWrapper;