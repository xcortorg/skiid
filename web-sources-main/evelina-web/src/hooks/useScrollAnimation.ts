import { useEffect } from 'react';

export function useScrollAnimation() {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Add small random delay for staggered animation
          setTimeout(() => {
            entry.target.classList.add('animate-fade-in');
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
          }, Math.random() * 200);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px'
    });

    // Select and observe all elements with scroll-fade class
    document.querySelectorAll('.scroll-fade').forEach(element => {
      element.style.opacity = '0';
      element.style.transform = 'translateY(40px)';
      element.style.transition = 'all 1s cubic-bezier(0.22, 1, 0.36, 1)';
      observer.observe(element);
    });

    return () => observer.disconnect();
  }, []);
}