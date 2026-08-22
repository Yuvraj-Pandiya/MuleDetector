import React, { useEffect, useRef } from 'react';

export default function NetworkCursorTrail() {
  const canvasRef = useRef(null);

  useEffect(() => {
    // 1. Accessibility & Device Checks
    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (isTouchDevice || prefersReducedMotion) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    let width = 0;
    let height = 0;
    let dpr = 1;

    // Mouse tracking state
    const mouse = {
      x: -100,
      y: -100,
      targetX: -100,
      targetY: -100,
      lastX: -100,
      lastY: -100,
      speed: 0,
      isMoving: false,
      stopTimer: null,
      active: false,
    };

    // Responsive Canvas Resize
    const handleResize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.scale(dpr, dpr);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    // Node Storage (Strictly capped pool for performance)
    const MAX_NODES = 16;
    const nodes = [];

    class Node {
      constructor(x, y, speed) {
        // Slight organic dispersion around cursor
        const angle = Math.random() * Math.PI * 2;
        const spread = 4 + Math.random() * 12;
        
        this.x = x + Math.cos(angle) * spread;
        this.y = y + Math.sin(angle) * spread;
        
        // Gentle inertia away from velocity vector
        this.vx = (Math.random() - 0.5) * 0.8 + (Math.random() - 0.5) * speed * 0.15;
        this.vy = (Math.random() - 0.5) * 0.8 + (Math.random() - 0.5) * speed * 0.15;
        
        this.radius = 1.2 + Math.random() * 1.4; // 1.2px - 2.6px (Tiny)
        this.maxLife = 35 + Math.floor(Math.random() * 25);
        this.life = this.maxLife;
        this.baseAlpha = 0.5 + Math.random() * 0.3;
        this.alpha = this.baseAlpha;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;
        
        // Drag / Friction
        this.vx *= 0.94;
        this.vy *= 0.94;

        this.life -= 1;
        // Smooth exponential fade out
        const lifeRatio = Math.max(0, this.life / this.maxLife);
        this.alpha = this.baseAlpha * Math.pow(lifeRatio, 1.5);
      }

      draw(context) {
        if (this.alpha <= 0.01) return;
        
        context.save();
        context.beginPath();
        context.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        
        // Subtle cyan/blue gradient theme match
        context.fillStyle = `rgba(147, 197, 253, ${this.alpha})`;
        context.shadowColor = 'rgba(59, 130, 246, 0.4)';
        context.shadowBlur = 4;
        context.fill();
        context.restore();
      }
    }

    // Mouse Movement Event Listener
    const handleMouseMove = (e) => {
      const x = e.clientX;
      const y = e.clientY;

      if (!mouse.active) {
        mouse.x = x;
        mouse.y = y;
        mouse.lastX = x;
        mouse.lastY = y;
        mouse.active = true;
      }

      mouse.targetX = x;
      mouse.targetY = y;
      mouse.isMoving = true;

      // Calculate Speed
      const dx = x - mouse.lastX;
      const dy = y - mouse.lastY;
      mouse.speed = Math.hypot(dx, dy);

      mouse.lastX = x;
      mouse.lastY = y;

      // Spawn Node on Movement
      if (mouse.speed > 0.5 && nodes.length < MAX_NODES) {
        nodes.push(new Node(x, y, mouse.speed));
      }

      // Reset Stop Timer
      if (mouse.stopTimer) clearTimeout(mouse.stopTimer);
      mouse.stopTimer = setTimeout(() => {
        mouse.isMoving = false;
        mouse.speed = 0;
      }, 120);
    };

    const handleMouseLeave = () => {
      mouse.active = false;
      mouse.isMoving = false;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);

    // Animation Frame Loop
    const CONNECT_DIST = 75; // Hairline connection threshold (px)
    
    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // Smooth cursor lerp
      if (mouse.active) {
        mouse.x += (mouse.targetX - mouse.x) * 0.35;
        mouse.y += (mouse.targetY - mouse.y) * 0.35;
      }

      // Update and Draw Nodes
      for (let i = nodes.length - 1; i >= 0; i--) {
        const node = nodes[i];
        node.update();

        if (node.life <= 0 || node.alpha <= 0.005) {
          nodes.splice(i, 1);
        } else {
          node.draw(ctx);
        }
      }

      // Draw Network Topology Connecting Lines
      const activeCount = nodes.length;
      for (let i = 0; i < activeCount; i++) {
        const a = nodes[i];

        // Connect node to cursor if close
        if (mouse.active) {
          const cDx = mouse.x - a.x;
          const cDy = mouse.y - a.y;
          const cDist = Math.hypot(cDx, cDy);

          if (cDist < CONNECT_DIST) {
            const lineAlpha = (1 - cDist / CONNECT_DIST) * a.alpha * 0.35;
            if (lineAlpha > 0.01) {
              ctx.save();
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(mouse.x, mouse.y);
              ctx.strokeStyle = `rgba(96, 165, 250, ${lineAlpha})`;
              ctx.lineWidth = 0.7;
              ctx.stroke();
              ctx.restore();
            }
          }
        }

        // Connect nearby nodes together
        for (let j = i + 1; j < activeCount; j++) {
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy);

          if (dist < CONNECT_DIST) {
            const minAlpha = Math.min(a.alpha, b.alpha);
            const lineAlpha = (1 - dist / CONNECT_DIST) * minAlpha * 0.3;

            if (lineAlpha > 0.01) {
              ctx.save();
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.strokeStyle = `rgba(147, 197, 253, ${lineAlpha})`;
              ctx.lineWidth = 0.6;
              ctx.stroke();
              ctx.restore();
            }
          }
        }
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      if (mouse.stopTimer) clearTimeout(mouse.stopTimer);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-[45] block"
      aria-hidden="true"
    />
  );
}
