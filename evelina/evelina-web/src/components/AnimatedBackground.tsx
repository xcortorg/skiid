import React, { useEffect, useRef } from 'react';

interface Dot {
  x: number;
  y: number;
  radius: number;
  color: string;
  alpha: number;
  dx: number;
  dy: number;
  originalAlpha: number;
  pulseSpeed: number;
  pulseOffset: number;
  angle: number;
  speed: number;
  distance: number;
  wave: {
    amplitude: number;
    frequency: number;
    offset: number;
  };
}

interface ShootingStar {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  alpha: number;
  decay: number;
  active: boolean;
  width: number;
  trail: { x: number; y: number; alpha: number }[];
}

const colors = [
  'rgba(114, 155, 176, 0.15)', // theme color
  'rgba(15, 23, 42, 0.15)',    // slate-900
  'rgba(2, 6, 23, 0.15)',      // darker blue
  'rgba(10, 10, 10, 0.15)',    // near black
  'rgba(17, 24, 39, 0.15)'     // gray-900
];

function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dotsRef = useRef<Dot[]>([]);
  const shootingStarsRef = useRef<ShootingStar[]>([]);
  const animationFrameRef = useRef<number>();
  const lastShootingStarTime = useRef(0);
  const centerXRef = useRef(0);
  const centerYRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const container = canvas.parentElement;
      if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        centerXRef.current = canvas.width / 2;
        centerYRef.current = canvas.height / 2;
      }
    };

    const createDots = () => {
      const dots: Dot[] = [];
      // Increase density of stars
      const numDots = Math.floor((canvas.width * canvas.height) / 4000);

      // Create a grid-based distribution for more even coverage
      const gridSize = Math.sqrt((canvas.width * canvas.height) / numDots);
      
      for (let x = 0; x < canvas.width; x += gridSize) {
        for (let y = 0; y < canvas.height; y += gridSize) {
          // Add random offset within each grid cell
          const offsetX = (Math.random() - 0.5) * gridSize;
          const offsetY = (Math.random() - 0.5) * gridSize;
          
          const posX = x + offsetX;
          const posY = y + offsetY;
          
          // Calculate distance from center for swirl effect
          const dx = posX - centerXRef.current;
          const dy = posY - centerYRef.current;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const angle = Math.atan2(dy, dx);

          // Vary star sizes with smaller range
          const radius = Math.random() * 1.2 + 0.3;
          
          dots.push({
            x: posX,
            y: posY,
            radius,
            color: colors[Math.floor(Math.random() * colors.length)],
            alpha: Math.random() * 0.4 + 0.1,
            dx: (Math.random() - 0.5) * 0.2,
            dy: (Math.random() - 0.5) * 0.2,
            originalAlpha: Math.random() * 0.4 + 0.1,
            pulseSpeed: Math.random() * 0.002 + 0.0005,
            pulseOffset: Math.random() * Math.PI * 2,
            angle,
            speed: Math.random() * 0.1 + 0.02,
            distance,
            wave: {
              amplitude: Math.random() * 0.8 + 0.2,
              frequency: Math.random() * 0.008 + 0.002,
              offset: Math.random() * Math.PI * 2
            }
          });
        }
      }

      return dots;
    };

    const createShootingStar = (): ShootingStar => {
      const angle = Math.PI / 4 + (Math.random() * Math.PI / 4);
      return {
        x: Math.random() * canvas.width,
        y: 0,
        length: Math.random() * 80 + 40,
        speed: Math.random() * 5 + 3,
        angle,
        alpha: 1,
        decay: 0.015 + Math.random() * 0.025,
        active: true,
        width: Math.random() * 1.5 + 0.3,
        trail: []
      };
    };

    const drawShootingStar = (ctx: CanvasRenderingContext2D, star: ShootingStar) => {
      star.trail.push({
        x: star.x,
        y: star.y,
        alpha: star.alpha
      });

      if (star.trail.length > 12) {
        star.trail.shift();
      }

      ctx.beginPath();
      ctx.moveTo(star.x, star.y);

      const gradient = ctx.createLinearGradient(
        star.x,
        star.y,
        star.x - Math.cos(star.angle) * star.length,
        star.y - Math.sin(star.angle) * star.length
      );
      
      gradient.addColorStop(0, `rgba(255, 255, 255, ${star.alpha})`);
      gradient.addColorStop(0.1, `rgba(114, 155, 176, ${star.alpha * 0.8})`);
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.strokeStyle = gradient;
      ctx.lineWidth = star.width;
      ctx.lineCap = 'round';
      ctx.stroke();

      star.trail.forEach((point, index) => {
        const trailAlpha = (index / star.trail.length) * point.alpha * 0.2;
        ctx.beginPath();
        ctx.arc(point.x, point.y, star.width * 0.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(114, 155, 176, ${trailAlpha})`;
        ctx.fill();
      });
    };

    const animate = () => {
      if (!ctx || !canvas) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      dotsRef.current.forEach(dot => {
        const time = Date.now() * 0.001;
        
        // Gentle swirl motion
        dot.angle += dot.speed * 0.008;
        const targetDistance = dot.distance + Math.sin(time + dot.pulseOffset) * 15;
        const x = centerXRef.current + Math.cos(dot.angle) * targetDistance;
        const y = centerYRef.current + Math.sin(dot.angle) * targetDistance;
        
        dot.x += (x - dot.x) * 0.03;
        dot.y += (y - dot.y) * 0.03;

        const waveOffset = Math.sin(time * dot.wave.frequency + dot.wave.offset) * dot.wave.amplitude;
        dot.distance += waveOffset * 0.03;

        dot.alpha = dot.originalAlpha + 
          Math.sin(time * 2 + dot.pulseOffset) * 0.08;

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, dot.radius, 0, Math.PI * 2);
        const color = dot.color.replace(/[\d.]+\)$/g, `${dot.alpha})`);
        ctx.fillStyle = color;
        ctx.fill();
      });

      const currentTime = Date.now();
      if (currentTime - lastShootingStarTime.current > 2500 && Math.random() < 0.15) {
        const numStars = Math.floor(Math.random() * 3) + 1;
        for (let i = 0; i < numStars; i++) {
          shootingStarsRef.current.push(createShootingStar());
        }
        lastShootingStarTime.current = currentTime;
      }

      shootingStarsRef.current = shootingStarsRef.current.filter(star => {
        if (!star.active) return false;

        star.x += Math.cos(star.angle) * star.speed;
        star.y += Math.sin(star.angle) * star.speed;
        star.alpha -= star.decay;

        if (star.alpha <= 0 || star.y > canvas.height || star.x < 0) {
          return false;
        }

        drawShootingStar(ctx, star);
        return true;
      });

      animationFrameRef.current = requestAnimationFrame(animate);
    };

    resizeCanvas();
    dotsRef.current = createDots();
    animate();

    window.addEventListener('resize', () => {
      resizeCanvas();
      dotsRef.current = createDots();
    });

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      window.removeEventListener('resize', resizeCanvas);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none select-none"
      style={{ 
        background: 'transparent',
        maxWidth: '100vw',
        maxHeight: '100vh'
      }}
    />
  );
}

export default AnimatedBackground;