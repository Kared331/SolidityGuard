import { useEffect, useRef } from 'react';
import styles from './InkVortex.module.css';

interface InkVortexProps {
  className?: string;
}

interface Particle {
  angle: number;
  radius: number;
  speed: number;
  size: number;
  alpha: number;
  red: boolean;
  ox: number;
  oy: number;
}

const INK = '31, 29, 24';
const VERMILION = '179, 54, 43';

/**
 * 墨点漩涡——Dashboard 卷首动画。
 *
 * 暖纸上一池缓缓旋转的墨：粒子沿椭圆轨道内快外慢地流动，
 * 混入约 2% 的朱砂粒子；鼠标划过会搅动附近的墨流。
 * 标题浮在中心的纸面亮区上（朱批语言，非直接复刻）。
 */
export default function InkVortex({ className }: InkVortexProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf = 0;
    let particles: Particle[] = [];
    let width = 0;
    let height = 0;
    const mouse = { x: -9999, y: -9999 };
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const spawn = () => {
      // 轨道半径必须完整落在带内（y 方向有 0.86 压扁），否则粒子被裁剪成碎屑
      const maxR = Math.min(width * 0.32, height * 0.55);
      const count = Math.min(2000, Math.floor(maxR * 9));
      particles = Array.from({ length: count }, () => {
        const radius = Math.pow(Math.random(), 0.5) * maxR + 14;
        const t = 1 - Math.min(radius / maxR, 1);
        return {
          angle: Math.random() * Math.PI * 2,
          radius,
          speed: 0.12 + 0.6 * t * t,
          size: 0.6 + Math.random() * 1.3,
          alpha: 0.2 + Math.random() * 0.5,
          red: Math.random() < 0.025,
          ox: 0,
          oy: 0,
        };
      });
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      spawn();
      if (reduced) drawFrame(0, true);
    };

    const drawFrame = (dt: number, staticFrame = false) => {
      const cx = width / 2;
      const cy = height / 2;
      ctx.clearRect(0, 0, width, height);

      // 中心纸面亮区——保证标题可读，呼应"漩涡中心透光"
      const glowR = Math.min(width * 0.24, height * 0.42);
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, glowR);
      glow.addColorStop(0, 'rgba(253, 252, 249, 0.88)');
      glow.addColorStop(0.6, 'rgba(253, 252, 249, 0.35)');
      glow.addColorStop(1, 'rgba(253, 252, 249, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      ctx.lineCap = 'round';
      for (const p of particles) {
        if (!staticFrame) {
          p.angle += p.speed * dt;
          p.ox *= 0.9;
          p.oy *= 0.9;
        }

        const tailAngle = p.angle - p.speed * 0.09;
        const x = cx + Math.cos(p.angle) * p.radius + p.ox;
        const y = cy + Math.sin(p.angle) * p.radius * 0.86 + p.oy;
        const px = cx + Math.cos(tailAngle) * p.radius + p.ox;
        const py = cy + Math.sin(tailAngle) * p.radius * 0.86 + p.oy;

        // 鼠标搅墨：靠近光标的粒子被推开
        if (!staticFrame && mouse.x >= 0) {
          const dx = x - mouse.x;
          const dy = y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 90 && dist > 0.01) {
            const f = ((90 - dist) / 90) * 2.2;
            p.ox += (dx / dist) * f;
            p.oy += (dy / dist) * f;
          }
        }

        const rgb = p.red ? VERMILION : INK;
        ctx.strokeStyle = `rgba(${rgb}, ${p.alpha})`;
        ctx.lineWidth = p.size;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(x, y);
        ctx.stroke();
      }
    };

    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      drawFrame(dt);
      raf = requestAnimationFrame(loop);
    };

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };
    const onMouseLeave = () => {
      mouse.x = -9999;
      mouse.y = -9999;
    };

    const ro = new ResizeObserver(() => resize());
    ro.observe(canvas);
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseleave', onMouseLeave);
    resize();

    if (!reduced) {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener('mousemove', onMouseMove);
      canvas.removeEventListener('mouseleave', onMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={className ? `${styles['vortex']} ${className}` : styles['vortex']}
      aria-hidden="true"
    />
  );
}
