(() => {
  const card = document.querySelector('[data-birthday-card]');
  if (!card) {
    console.error('[birthday-card] Motion runtime could not find the card root.');
    return;
  }

  const profiles = {
    '01': {
      name: 'royal',
      shape: 'sparkle',
      geometry: 'diamond',
      colors: ['rgba(223, 178, 102, 0.82)', 'rgba(253, 230, 138, 0.72)'],
      threeColors: [0xdfb266, 0xfde68a],
      entrance: [{ opacity: 0, transform: 'translateY(18px) scale(0.98)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'scale(1)' }, { transform: 'scale(1.025)' }, { transform: 'scale(1)' }],
      targets: ['#cakeBox'],
    },
    '02': {
      name: 'emerald',
      shape: 'gem',
      geometry: 'octahedron',
      colors: ['rgba(52, 211, 153, 0.76)', 'rgba(212, 175, 55, 0.72)'],
      threeColors: [0x34d399, 0xd4af37],
      entrance: [{ opacity: 0, transform: 'rotateY(-9deg) scale(0.94)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'scale(1) rotate(0deg)' }, { transform: 'scale(1.018) rotate(0.8deg)' }, { transform: 'scale(1)' }],
      targets: ['#gemHolder'],
    },
    '04': {
      name: 'ruby',
      shape: 'ember',
      geometry: 'icosahedron',
      colors: ['rgba(248, 113, 113, 0.78)', 'rgba(251, 191, 36, 0.76)'],
      threeColors: [0xf87171, 0xfbbf24],
      entrance: [{ opacity: 0, transform: 'translateY(18px) scale(0.96)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ filter: 'brightness(1)' }, { filter: 'brightness(1.12)' }, { filter: 'brightness(1)' }],
      targets: [],
    },
    '05': {
      name: 'cyber',
      shape: 'circuit',
      geometry: 'cube',
      colors: ['rgba(56, 189, 248, 0.76)', 'rgba(129, 140, 248, 0.76)'],
      threeColors: [0x38bdf8, 0x818cf8],
      entrance: [{ opacity: 0, transform: 'translateX(-20px)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'translateY(0)' }, { transform: 'translateY(-5px)' }, { transform: 'translateY(0)' }],
      targets: [],
    },
    '06': {
      name: 'botanical',
      shape: 'petal',
      geometry: 'leaf',
      colors: ['rgba(134, 169, 133, 0.78)', 'rgba(231, 214, 164, 0.72)'],
      threeColors: [0x86a985, 0xe7d6a4],
      entrance: [{ opacity: 0, transform: 'translateY(14px) scale(0.97)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'scale(1)' }, { transform: 'scale(1.015)' }, { transform: 'scale(1)' }],
      targets: [],
    },
    '07': {
      name: 'galaxy',
      shape: 'star',
      geometry: 'torus',
      colors: ['rgba(196, 181, 253, 0.8)', 'rgba(253, 224, 71, 0.78)'],
      threeColors: [0xc4b5fd, 0xfde047],
      entrance: [{ opacity: 0, transform: 'rotateX(8deg) scale(0.95)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'scale(1)' }, { transform: 'scale(1.02) rotate(-0.6deg)' }, { transform: 'scale(1)' }],
      targets: [],
    },
    '08': {
      name: 'sunrise',
      shape: 'lantern',
      geometry: 'cone',
      colors: ['rgba(251, 146, 60, 0.8)', 'rgba(253, 230, 138, 0.76)'],
      threeColors: [0xfb923c, 0xfde68a],
      entrance: [{ opacity: 0, transform: 'translateY(24px)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'translateY(0)' }, { transform: 'translateY(-6px)' }, { transform: 'translateY(0)' }],
      targets: [],
    },
    '09': {
      name: 'parchment',
      shape: 'seal',
      geometry: 'torus',
      colors: ['rgba(200, 169, 106, 0.78)', 'rgba(232, 215, 170, 0.72)'],
      threeColors: [0xc8a96a, 0xe8d7aa],
      entrance: [{ opacity: 0, transform: 'perspective(900px) rotateX(-8deg) translateY(14px)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'scale(1) rotate(0deg)' }, { transform: 'scale(1.015) rotate(-0.4deg)' }, { transform: 'scale(1)' }],
      targets: ['#waxSeal'],
    },
    '10': {
      name: 'party',
      shape: 'confetti',
      geometry: 'confetti',
      colors: ['rgba(251, 113, 133, 0.8)', 'rgba(250, 204, 21, 0.8)'],
      threeColors: [0xfb7185, 0xfacc15],
      entrance: [{ opacity: 0, transform: 'translateY(16px) scale(0.92)' }, { opacity: 1, transform: 'none' }],
      celebration: [{ transform: 'rotate(0deg) scale(1)' }, { transform: 'rotate(1deg) scale(1.02)' }, { transform: 'rotate(0deg) scale(1)' }],
      targets: [],
    },
  };

  const layout = card.dataset.birthdayCard;
  const profile = profiles[layout];
  if (!profile) {
    console.error(`[birthday-card] No motion profile is registered for layout ${layout || '(missing)'}.`);
    return;
  }

  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  const desktopPointer = window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches ?? false;
  const cleanup = [];
  const disposableMaterials = [];
  let renderer;
  let scene;
  let camera;
  let particleField;
  let ornaments = [];
  let context;
  let canvas;
  let particles = [];
  let frameId = 0;
  let lastFrameAt = 0;
  let disposed = false;
  let celebrationAnimation;

  function addListener(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    cleanup.push(() => target.removeEventListener(type, handler, options));
  }

  function fitCanvas(element) {
    Object.assign(element.style, {
      position: 'fixed',
      inset: '0',
      width: 'auto',
      height: 'auto',
      pointerEvents: 'none',
      zIndex: '0',
    });
    element.setAttribute('aria-hidden', 'true');
  }

  function getCanvas() {
    canvas = document.querySelector('body > canvas:not(#silkCanvas)');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'birthday-motion-canvas';
      document.body.prepend(canvas);
    }
    fitCanvas(canvas);
    return canvas;
  }

  function setViewportSize() {
    const viewport = window.visualViewport;
    return {
      width: Math.max(1, Math.round(viewport?.width || window.innerWidth || 1)),
      height: Math.max(1, Math.round(viewport?.height || window.innerHeight || 1)),
    };
  }

  function resizeCanvas() {
    if (!canvas) return;
    const { width, height } = setViewportSize();
    const maxRatio = width < 600 ? 1.25 : 1.35;
    const ratio = Math.min(window.devicePixelRatio || 1, maxRatio);
    canvas.width = Math.max(1, Math.round(width * ratio));
    canvas.height = Math.max(1, Math.round(height * ratio));
    if (renderer) {
      renderer.setPixelRatio(ratio);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    } else if (context) {
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      particles = makeParticles(width, height);
      drawCanvas(0, width, height);
    }
  }

  function makeGeometry(THREE, shape) {
    if (shape === 'diamond') return new THREE.TetrahedronGeometry(0.7, 0);
    if (shape === 'octahedron') return new THREE.OctahedronGeometry(0.78, 0);
    if (shape === 'icosahedron') return new THREE.IcosahedronGeometry(0.68, 0);
    if (shape === 'cube') return new THREE.BoxGeometry(0.65, 0.65, 0.65);
    if (shape === 'leaf') return new THREE.SphereGeometry(0.78, 10, 8);
    if (shape === 'cone') return new THREE.ConeGeometry(0.5, 1.2, 5);
    if (shape === 'confetti') return new THREE.BoxGeometry(0.66, 0.18, 0.06);
    return new THREE.TorusGeometry(0.72, 0.025, 5, 40);
  }

  function setupThree() {
    if (!window.THREE) return false;
    try {
      const THREE = window.THREE;
      const { width, height } = setViewportSize();
      const ratio = Math.min(window.devicePixelRatio || 1, width < 600 ? 1.25 : 1.35);
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: false,
        powerPreference: 'low-power',
      });
      renderer.setPixelRatio(ratio);
      renderer.setSize(width, height, false);
      renderer.setClearColor(0x000000, 0);
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(52, width / height, 0.1, 70);
      camera.position.z = 18;

      const mobile = width < 600;
      const particleCount = mobile ? 32 : 68;
      const positions = new Float32Array(particleCount * 3);
      for (let index = 0; index < particleCount; index += 1) {
        positions[index * 3] = (Math.random() - 0.5) * 26;
        positions[index * 3 + 1] = (Math.random() - 0.5) * 16;
        positions[index * 3 + 2] = -Math.random() * 20;
      }
      const particleGeometry = new THREE.BufferGeometry();
      particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const particleMaterial = new THREE.PointsMaterial({
        color: profile.threeColors[0],
        size: mobile ? 0.12 : 0.14,
        transparent: true,
        opacity: 0.56,
        sizeAttenuation: true,
        depthWrite: false,
      });
      disposableMaterials.push(particleMaterial);
      particleField = new THREE.Points(particleGeometry, particleMaterial);
      scene.add(particleField);

      const ornamentGeometry = makeGeometry(THREE, profile.geometry);
      const ornamentCount = mobile ? 3 : 5;
      for (let index = 0; index < ornamentCount; index += 1) {
        const ornamentMaterial = new THREE.MeshBasicMaterial({
          color: profile.threeColors[index % profile.threeColors.length],
          wireframe: profile.geometry !== 'confetti',
          transparent: true,
          opacity: 0.16,
          depthWrite: false,
        });
        disposableMaterials.push(ornamentMaterial);
        const ornament = new THREE.Mesh(
          ornamentGeometry,
          ornamentMaterial,
        );
        const side = index % 2 ? 1 : -1;
        ornament.position.set(side * (4.2 + index * 0.36), (index - 2) * 2.6, -1 - index * 1.6);
        if (profile.geometry === 'leaf') ornament.scale.set(0.55, 1.25, 0.22);
        else ornament.scale.setScalar(0.9 + (index % 3) * 0.24);
        scene.add(ornament);
        ornaments.push(ornament);
      }
      canvas.dataset.motionMode = 'webgl';
      return true;
    } catch (error) {
      console.error(`[birthday-card:${layout}] WebGL initialization failed; switching to Canvas 2D.`, error);
      renderer?.dispose();
      renderer = undefined;
      return false;
    }
  }

  function makeParticles(width, height) {
    const count = width < 600 ? 18 : 34;
    return Array.from({ length: count }, (_, index) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: 1.4 + Math.random() * (profile.shape === 'confetti' ? 4 : 2.6),
      phase: Math.random() * Math.PI * 2,
      speed: 0.08 + Math.random() * 0.24,
      drift: (Math.random() - 0.5) * 0.34,
      color: profile.colors[index % profile.colors.length],
    }));
  }

  function drawStar(particle) {
    context.beginPath();
    for (let point = 0; point < 10; point += 1) {
      const angle = -Math.PI / 2 + point * Math.PI / 5;
      const radius = particle.radius * (point % 2 ? 0.42 : 1);
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      if (point === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    }
    context.closePath();
    context.fill();
  }

  function drawShape(particle, time) {
    context.save();
    context.translate(particle.x, particle.y);
    context.rotate(particle.phase + time * particle.speed * 0.18);
    context.globalAlpha = 0.36 + (Math.sin(time * 0.001 + particle.phase) + 1) * 0.2;
    context.fillStyle = particle.color;

    if (profile.shape === 'sparkle' || profile.shape === 'star') {
      drawStar(particle);
    } else if (profile.shape === 'petal') {
      context.beginPath();
      context.moveTo(0, -particle.radius * 1.5);
      context.quadraticCurveTo(particle.radius * 1.4, 0, 0, particle.radius * 1.7);
      context.quadraticCurveTo(-particle.radius * 1.4, 0, 0, -particle.radius * 1.5);
      context.fill();
    } else if (profile.shape === 'circuit') {
      context.fillRect(-particle.radius * 1.4, -0.7, particle.radius * 2.8, 1.4);
      context.fillRect(-0.7, -particle.radius * 1.4, 1.4, particle.radius * 2.8);
    } else if (profile.shape === 'confetti') {
      context.fillRect(-particle.radius * 0.55, -particle.radius * 0.95, particle.radius * 1.1, particle.radius * 1.9);
    } else if (profile.shape === 'lantern') {
      context.strokeStyle = particle.color;
      context.lineWidth = 1.4;
      context.strokeRect(-particle.radius * 0.62, -particle.radius, particle.radius * 1.24, particle.radius * 2);
      context.beginPath();
      context.moveTo(0, -particle.radius * 1.35);
      context.lineTo(0, particle.radius * 1.3);
      context.stroke();
    } else if (profile.shape === 'seal') {
      context.beginPath();
      context.arc(0, 0, particle.radius, 0, Math.PI * 2);
      context.strokeStyle = particle.color;
      context.lineWidth = 1;
      context.stroke();
    } else {
      context.beginPath();
      context.moveTo(0, -particle.radius);
      context.lineTo(particle.radius, 0);
      context.lineTo(0, particle.radius);
      context.lineTo(-particle.radius, 0);
      context.closePath();
      context.fill();
    }
    context.restore();
  }

  function drawCanvas(time, width, height) {
    if (!context) return;
    context.clearRect(0, 0, width, height);
    for (const particle of particles) {
      particle.y -= particle.speed * (profile.shape === 'lantern' ? 0.8 : 0.38);
      particle.x += particle.drift + Math.sin(time * 0.0005 + particle.phase) * 0.13;
      if (particle.y < -12) {
        particle.y = height + 10;
        particle.x = Math.random() * width;
      }
      if (particle.x < -12) particle.x = width + 8;
      if (particle.x > width + 12) particle.x = -8;
      drawShape(particle, time);
    }
  }

  function setupCanvasFallback() {
    try {
      context = canvas.getContext('2d', { alpha: true });
      if (!context) {
        canvas = document.createElement('canvas');
        canvas.id = 'birthday-motion-canvas';
        document.body.prepend(canvas);
        fitCanvas(canvas);
        context = canvas.getContext('2d', { alpha: true });
      }
      if (!context) throw new Error('Canvas 2D is unavailable.');
      canvas.dataset.motionMode = 'canvas-2d';
      resizeCanvas();
      console.warn(`[birthday-card:${layout}] WebGL is unavailable; using the lightweight ${profile.name} Canvas 2D effect.`);
      return true;
    } catch (error) {
      console.error(`[birthday-card:${layout}] Canvas fallback initialization failed.`, error);
      context = undefined;
      return false;
    }
  }

  function render(time = 0) {
    if (disposed || document.hidden) return;
    const { width, height } = setViewportSize();
    if (!lastFrameAt || time - lastFrameAt >= 1000 / (width < 600 ? 24 : 30)) {
      if (renderer) {
        particleField.rotation.y = time * 0.00012;
        particleField.rotation.x = Math.sin(time * 0.00012) * 0.06;
        ornaments.forEach((ornament, index) => {
          ornament.rotation.x += 0.0003 + index * 0.00005;
          ornament.rotation.y += 0.00045 + index * 0.00008;
        });
        renderer.render(scene, camera);
      } else {
        drawCanvas(time, width, height);
      }
      lastFrameAt = time;
    }
    if (!reduceMotion) frameId = window.requestAnimationFrame(render);
  }

  function stopRender() {
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    lastFrameAt = 0;
  }

  function startRender() {
    if (!reduceMotion && !document.hidden && !frameId && window.requestAnimationFrame) {
      frameId = window.requestAnimationFrame(render);
    }
  }

  function onVisibilityChange() {
    stopRender();
    if (!document.hidden) {
      if (reduceMotion) render(0);
      else startRender();
    }
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    stopRender();
    cleanup.forEach((remove) => remove());
    ornaments.forEach((ornament) => ornament.geometry.dispose());
    particleField?.geometry.dispose();
    disposableMaterials.forEach((material) => material.dispose());
    if (renderer) {
      renderer.dispose();
      renderer.forceContextLoss?.();
    }
  }

  function playEntrance() {
    if (reduceMotion) return;
    if (typeof card.animate === 'function') {
      card.animate(profile.entrance, {
        duration: 720,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      });
    }
  }

  function celebrate(target) {
    status.textContent = '';
    status.textContent = 'Chúc mừng sinh nhật! Chúc một tuổi mới nhiều niềm vui.';
    card.querySelector('#candleFlames')?.classList.add('blown');
    if (reduceMotion) return;

    const bounds = (target || card).getBoundingClientRect();
    if (window.confetti) {
      window.confetti({
        particleCount: window.innerWidth < 600 ? 34 : 62,
        spread: profile.name === 'party' ? 92 : 66,
        startVelocity: 30,
        origin: {
          x: Math.min(0.92, Math.max(0.08, (bounds.left + bounds.width / 2) / Math.max(window.innerWidth, 1))),
          y: Math.min(0.88, Math.max(0.12, (bounds.top + bounds.height / 2) / Math.max(window.innerHeight, 1))),
        },
        colors: profile.threeColors.map((color) => `#${color.toString(16).padStart(6, '0')}`),
      });
    }
    if (window.gsap) {
      window.gsap.fromTo(card, { scale: 1 }, {
        scale: 1.018,
        yoyo: true,
        repeat: 1,
        duration: 0.18,
        ease: 'power1.inOut',
      });
    } else if (typeof card.animate === 'function') {
      celebrationAnimation?.cancel();
      celebrationAnimation = card.animate(profile.celebration, {
        duration: profile.name === 'party' ? 520 : 440,
        easing: 'ease-out',
      });
    }
    if (target && typeof target.animate === 'function' && target !== card) {
      target.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.08)' }, { transform: 'scale(1)' }], {
        duration: 420,
        easing: 'ease-out',
      });
    }
  }

  function handlePointerMove(event) {
    if (!desktopPointer || event.pointerType === 'touch') return;
    const bounds = card.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / Math.max(bounds.width, 1);
    const y = (event.clientY - bounds.top) / Math.max(bounds.height, 1);
    card.style.transform = `perspective(900px) rotateX(${(0.5 - y) * 2.6}deg) rotateY(${(x - 0.5) * 3.2}deg)`;
  }

  function resetPointerTilt() {
    card.style.transform = '';
  }

  function makeFocusable(target) {
    target.setAttribute('role', 'button');
    target.setAttribute('tabindex', '0');
    if (!target.hasAttribute('aria-label') && target.title) target.setAttribute('aria-label', target.title);
    const activate = () => celebrate(target);
    const onKeyDown = (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        activate();
      }
    };
    addListener(target, 'click', activate);
    addListener(target, 'keydown', onKeyDown);
  }

  canvas = getCanvas();
  if (window.getComputedStyle(card).position === 'static') card.style.position = 'relative';
  card.style.zIndex = card.style.zIndex || '2';
  card.style.transformStyle = 'preserve-3d';
  card.dataset.motionProfile = profile.name;
  card.dataset.motionState = 'active';

  const status = document.createElement('span');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  Object.assign(status.style, {
    position: 'absolute',
    width: '1px',
    height: '1px',
    padding: '0',
    margin: '-1px',
    overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)',
    whiteSpace: 'nowrap',
    border: '0',
  });
  card.append(status);

  const setup = setupThree();
  if (!setup && !setupCanvasFallback()) card.dataset.motionState = 'css-fallback';
  resizeCanvas();
  if (reduceMotion) render(0);
  else startRender();

  playEntrance();
  if (desktopPointer && !reduceMotion) {
    addListener(card, 'pointermove', handlePointerMove, { passive: true });
    addListener(card, 'pointerleave', resetPointerTilt, { passive: true });
  }
  card.querySelectorAll('button').forEach((button) => addListener(button, 'click', () => celebrate(button)));
  profile.targets.forEach((selector) => {
    const target = card.querySelector(selector);
    if (target) makeFocusable(target);
  });

  const resize = () => resizeCanvas();
  addListener(window, 'resize', resize, { passive: true });
  addListener(window, 'orientationchange', resize, { passive: true });
  if (window.visualViewport) addListener(window.visualViewport, 'resize', resize, { passive: true });
  addListener(document, 'visibilitychange', onVisibilityChange);
  addListener(window, 'pagehide', dispose, { once: true });
})();
