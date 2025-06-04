import React, { useEffect, useRef } from 'react';

function StarField() {
  const containerRef = useRef<HTMLDivElement>(null);
  const starsRef = useRef<HTMLDivElement[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const numStars = 100;
    starsRef.current = [];

    for (let i = 0; i < numStars; i++) {
      const star = document.createElement('div');
      star.className = 'star';
      
      const layerRandom = Math.random();
      const layer = layerRandom < 0.5 ? 1 : layerRandom < 0.8 ? 2 : 3;
      star.setAttribute('data-layer', layer.toString());
      
      const verticalBias = Math.pow(Math.random(), 3);
      star.style.top = `${verticalBias * 100}%`;
      star.style.left = `${Math.random() * 100}%`;
      
      switch(layer) {
        case 1:
          star.style.width = `${Math.random() * 2 + 2}px`;
          star.style.height = star.style.width;
          const topOpacity = 1 - (verticalBias * 0.3);
          star.style.opacity = topOpacity.toString();
          break;
        case 2:
          star.style.width = `${Math.random() * 1.5 + 1.5}px`;
          star.style.height = star.style.width;
          const midOpacity = 0.8 - (verticalBias * 0.4);
          star.style.opacity = midOpacity.toString();
          break;
        case 3:
          star.style.width = `${Math.random() * 1 + 1}px`;
          star.style.height = star.style.width;
          const farOpacity = 0.6 - (verticalBias * 0.4);
          star.style.opacity = farOpacity.toString();
          break;
      }
      
      const baseSpeed = 2 + Math.random() * 4;
      const speedMultiplier = 1 + verticalBias;
      const duration = baseSpeed * speedMultiplier;
      star.style.animationDuration = `${duration}s`;
      star.style.animationDelay = `${Math.random() * duration}s`;
      
      container.appendChild(star);
      starsRef.current.push(star);
    }

    const handleScroll = () => {
      const scrollY = window.scrollY;
      
      starsRef.current.forEach(star => {
        const layer = parseInt(star.getAttribute('data-layer') || '1');
        const verticalPosition = parseFloat(star.style.top) / 100;
        
        const baseSpeed = layer === 1 ? 0.5 : layer === 2 ? 0.3 : 0.1;
        const speedMultiplier = 1 - (verticalPosition * 0.5);
        const speed = baseSpeed * speedMultiplier;
        
        const yOffset = scrollY * speed;
        star.style.transform = `translateY(${yOffset}px)`;
      });
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      starsRef.current.forEach(star => star.remove());
    };
  }, []);

  return <div ref={containerRef} className="star-field fixed inset-0 pointer-events-none z-10" />;
}

export default StarField;