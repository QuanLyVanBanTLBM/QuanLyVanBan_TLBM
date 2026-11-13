(() => {
  const card = document.querySelector('[data-birthday-card]');
  if (!card) return;

  const layout = card.dataset.birthdayCard;
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  const palettes = {
    '01': [0xdfb266, 0xfde68a],
    '02': [0x34d399, 0xd4af37],
    '04': [0xf87171, 0xfbbf24],
    '05': [0x38bdf8, 0x818cf8],
    '06': [0x86a985, 0xe7d6a4],
    '07': [0xc4b5fd, 0xfde047],
    '08': [0xfb923c, 0xfde68a],
    '09': [0xc8a96a, 0xe8d7aa],
    '10': [0xfb7185, 0xfacc15],
  };
  const colors = palettes[layout] || palettes['01'];
  let canvas = document.querySelector('body > canvas:not(#silkCanvas)');

  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'birthday-motion-webgl';
    document.body.prepend(canvas);
  }

  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'fixed',
    inset: '0',
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: '1',
  });

  if (window.getComputedStyle(card).position === 'static') {
    card.style.position = 'relative';
  }
  card.style.zIndex = card.style.zIndex || '2';
  card.style.transformStyle = 'preserve-3d';

  let renderer;
  let frameId = 0;
  let scene;
  let camera;
  let particles;
  const ornaments = [];

  function resizeScene() {
    if (!renderer || !camera) return;
    const width = Math.max(window.innerWidth, 1);
    const height = Math.max(window.innerHeight, 1);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.35));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function setupScene() {
    if (!window.THREE) return false;

    try {
      const THREE = window.THREE;
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: 'low-power',
      });
      renderer.setClearColor(0x000000, 0);
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(52, 1, 0.1, 80);
      camera.position.z = 18;

      const count = window.innerWidth < 600 ? 72 : 150;
      const positions = new Float32Array(count * 3);
      for (let index = 0; index < count; index += 1) {
        positions[index * 3] = (Math.random() - 0.5) * 32;
        positions[index * 3 + 1] = (Math.random() - 0.5) * 18;
        positions[index * 3 + 2] = (Math.random() - 0.5) * 24;
      }
      const particleGeometry = new THREE.BufferGeometry();
      particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const particleMaterial = new THREE.PointsMaterial({
        color: colors[0],
        size: 0.11,
        transparent: true,
        opacity: 0.58,
        sizeAttenuation: true,
        depthWrite: false,
      });
      particles = new THREE.Points(particleGeometry, particleMaterial);
      scene.add(particles);

      const ringGeometry = new THREE.TorusGeometry(1.25, 0.018, 6, 72);
      for (let index = 0; index < 4; index += 1) {
        const ring = new THREE.Mesh(
          ringGeometry,
          new THREE.MeshBasicMaterial({
            color: colors[index % colors.length],
            transparent: true,
            opacity: 0.19,
            depthWrite: false,
          }),
        );
        ring.position.set(index % 2 ? 10.5 : -10.5, index < 2 ? 4 : -4, -2 - index);
        ring.rotation.set(index * 0.43, index * 0.31, index * 0.18);
        ring.scale.setScalar(1 + index * 0.14);
        scene.add(ring);
        ornaments.push(ring);
      }

      resizeScene();
      canvas.dataset.motionReady = 'true';
      return true;
    } catch {
      renderer?.dispose();
      renderer = undefined;
      return false;
    }
  }

  function render(timestamp = 0) {
    if (!renderer || document.hidden) return;
    if (!reduceMotion) {
      const time = timestamp * 0.00015;
      particles.rotation.y = time;
      particles.rotation.x = Math.sin(time) * 0.08;
      ornaments.forEach((ornament, index) => {
        ornament.rotation.z += 0.0005 + index * 0.00015;
        ornament.rotation.x += 0.00025;
      });
    }
    renderer.render(scene, camera);
    if (!reduceMotion) frameId = window.requestAnimationFrame(render);
  }

  if (setupScene()) {
    window.addEventListener('resize', resizeScene, { passive: true });
    document.addEventListener('visibilitychange', () => {
      if (frameId) window.cancelAnimationFrame(frameId);
      frameId = 0;
      if (!document.hidden) render();
    });
    render();
  }

  if (!reduceMotion && window.gsap) {
    window.gsap.from(card, {
      opacity: 0,
      y: 18,
      duration: 0.65,
      ease: 'power2.out',
      clearProps: 'opacity,transform',
    });
  }

  if (!reduceMotion && window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches) {
    card.addEventListener('pointermove', (event) => {
      const bounds = card.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / Math.max(bounds.width, 1);
      const y = (event.clientY - bounds.top) / Math.max(bounds.height, 1);
      const rotationX = (0.5 - y) * 2.8;
      const rotationY = (x - 0.5) * 3.6;
      if (window.gsap) {
        window.gsap.to(card, {
          rotationX,
          rotationY,
          transformPerspective: 1000,
          duration: 0.22,
          overwrite: true,
        });
      } else {
        card.style.transform = `perspective(62.5rem) rotateX(${rotationX}deg) rotateY(${rotationY}deg)`;
      }
    }, { passive: true });
    card.addEventListener('pointerleave', () => {
      if (window.gsap) {
        window.gsap.to(card, { rotationX: 0, rotationY: 0, duration: 0.35, overwrite: true });
      } else {
        card.style.transform = '';
      }
    }, { passive: true });
  }

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

  function celebrate(target) {
    status.textContent = 'Chúc mừng sinh nhật! Chúc một tuổi mới nhiều niềm vui.';
    if (target) target.setAttribute('aria-pressed', 'true');
    document.querySelector('#candleFlames')?.classList.add('blown');

    if (reduceMotion) return;
    if (window.confetti) {
      window.confetti({
        particleCount: 72,
        spread: 72,
        startVelocity: 34,
        origin: { y: 0.62 },
        colors: colors.map((color) => `#${color.toString(16).padStart(6, '0')}`),
      });
    }
    if (window.gsap) {
      window.gsap.fromTo(
        card,
        { scale: 1 },
        { scale: 1.018, yoyo: true, repeat: 1, duration: 0.18, ease: 'power1.inOut' },
      );
    }
  }

  document.querySelectorAll('button').forEach((button) => {
    button.addEventListener('click', () => celebrate(button));
  });

  document.querySelectorAll('#cakeBox, #gemHolder, #waxSeal').forEach((target) => {
    target.setAttribute('role', 'button');
    target.setAttribute('tabindex', '0');
    target.addEventListener('click', () => celebrate(target));
    target.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        celebrate(target);
      }
    });
  });
})();
