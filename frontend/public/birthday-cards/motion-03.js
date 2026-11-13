(() => {
  const canvas = document.getElementById('silkCanvas');
  const card = document.getElementById('paperCard');
  const button = document.getElementById('toastBtn');
  if (!canvas || !card || !button) return;

  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  const desktopPointer = window.matchMedia?.('(hover: hover) and (pointer: fine)')?.matches ?? false;
  const pointer = { x: 0, y: 0 };
  const vertexSource = `
    attribute vec2 aPosition;
    void main() {
      gl_Position = vec4(aPosition, 0.0, 1.0);
    }
  `;
  const fragmentSource = `
    precision mediump float;
    uniform vec2 uResolution;
    uniform vec2 uPointer;
    uniform float uTime;

    float fabricHeight(vec2 point, float time) {
      float bend = sin(point.y * 1.7 + time * 0.36 + uPointer.y * 0.8) * 0.23;
      float x = point.x + bend + uPointer.x * 0.08;
      return sin(x * 4.1 + time * 0.7) * 0.075
        + cos((x * 1.5 - point.y) * 5.1 - time * 0.45) * 0.04
        + sin(point.y * 3.2 + time * 0.32) * 0.03;
    }

    void main() {
      vec2 point = (gl_FragCoord.xy / uResolution - 0.5)
        * vec2(uResolution.x / uResolution.y, 1.0);
      float height = fabricHeight(point, uTime);
      float stepSize = 0.003;
      float slopeX = (fabricHeight(point + vec2(stepSize, 0.0), uTime)
        - fabricHeight(point - vec2(stepSize, 0.0), uTime)) / (2.0 * stepSize);
      float slopeY = (fabricHeight(point + vec2(0.0, stepSize), uTime)
        - fabricHeight(point - vec2(0.0, stepSize), uTime)) / (2.0 * stepSize);
      vec3 normal = normalize(vec3(-slopeX * 0.12, -slopeY * 0.12, 1.0));
      vec3 lightDirection = normalize(vec3(-0.48, 0.58, 0.85));
      float diffuse = max(dot(normal, lightDirection), 0.0);
      float sheen = pow(max(dot(normal, normalize(lightDirection + vec3(0.0, 0.0, 1.0))), 0.0), 12.0);
      float folds = 0.5 + 0.5 * sin(height * 42.0 + point.y * 3.5 + uTime * 0.4);
      vec3 shadowTone = vec3(0.42, 0.33, 0.23);
      vec3 lightTone = vec3(0.91, 0.83, 0.68);
      vec3 color = mix(shadowTone, lightTone, clamp(diffuse * 0.55 + folds * 0.28, 0.0, 1.0));
      color += sheen * vec3(0.25, 0.18, 0.09);
      gl_FragColor = vec4(color, 0.24 + diffuse * 0.1 + sheen * 0.16);
    }
  `;

  let gl = null;
  let context2d = null;
  let program = null;
  let resolutionLocation = null;
  let pointerLocation = null;
  let timeLocation = null;
  let frameId = 0;
  let cssWidth = 0;
  let cssHeight = 0;
  let pixelRatio = 1;
  let lastFrameAt = 0;
  const cleanup = [];

  function addListener(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    cleanup.push(() => target.removeEventListener(type, handler, options));
  }

  function compileShader(type, source) {
    const shader = gl.createShader(type);
    if (!shader) throw new Error('Unable to create WebGL shader.');
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || 'WebGL shader compilation failed.';
      gl.deleteShader(shader);
      throw new Error(message);
    }
    return shader;
  }

  function setupWebGL() {
    try {
      gl = canvas.getContext('webgl', { alpha: true, antialias: true, powerPreference: 'low-power' });
      if (!gl) return false;

      const vertexShader = compileShader(gl.VERTEX_SHADER, vertexSource);
      const fragmentShader = compileShader(gl.FRAGMENT_SHADER, fragmentSource);
      program = gl.createProgram();
      if (!program) return false;
      gl.attachShader(program, vertexShader);
      gl.attachShader(program, fragmentShader);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        throw new Error(gl.getProgramInfoLog(program) || 'WebGL program linking failed.');
      }

      gl.useProgram(program);
      const positionLocation = gl.getAttribLocation(program, 'aPosition');
      const positionBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
        -1, -1, 1, -1, -1, 1,
        -1, 1, 1, -1, 1, 1,
      ]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(positionLocation);
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.clearColor(0, 0, 0, 0);
      resolutionLocation = gl.getUniformLocation(program, 'uResolution');
      pointerLocation = gl.getUniformLocation(program, 'uPointer');
      timeLocation = gl.getUniformLocation(program, 'uTime');
      return true;
    } catch (error) {
      console.error('[birthday-card:03] WebGL initialization failed; using Canvas 2D fallback.', error);
      return false;
    }
  }

  function resize() {
    cssWidth = window.visualViewport?.width || window.innerWidth;
    cssHeight = window.visualViewport?.height || window.innerHeight;
    pixelRatio = Math.min(window.devicePixelRatio || 1, cssWidth < 600 ? 1.25 : 1.4);
    canvas.width = Math.max(1, Math.round(cssWidth * pixelRatio));
    canvas.height = Math.max(1, Math.round(cssHeight * pixelRatio));
    if (gl) {
      gl.viewport(0, 0, canvas.width, canvas.height);
    } else if (context2d) {
      context2d.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    }
    draw(0);
  }

  function drawFallback(time) {
    if (!context2d) return;
    context2d.clearRect(0, 0, cssWidth, cssHeight);
    context2d.lineCap = 'round';
    for (let line = 0; line < 8; line += 1) {
      const baseline = cssHeight * (0.18 + line * 0.1);
      const phase = time * 0.00035 + line * 0.62;
      context2d.beginPath();
      context2d.moveTo(0, baseline);
      for (let step = 1; step <= 12; step += 1) {
        const x = (cssWidth / 12) * step;
        const y = baseline + Math.sin((step / 12) * 6.2 + phase) * cssHeight * 0.025;
        context2d.lineTo(x, y);
      }
      context2d.strokeStyle = `rgba(154, 107, 38, ${0.08 + (line % 3) * 0.025})`;
      context2d.lineWidth = 1 + (line % 3) * 0.5;
      context2d.shadowColor = 'rgba(201, 167, 112, 0.28)';
      context2d.shadowBlur = 10;
      context2d.stroke();
    }
    context2d.shadowBlur = 0;
  }

  function draw(timestamp) {
    if (gl && program) {
      gl.useProgram(program);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      gl.uniform2f(pointerLocation, pointer.x, pointer.y);
      gl.uniform1f(timeLocation, timestamp / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
    } else {
      drawFallback(timestamp);
    }
  }

  function animate(timestamp) {
    if (document.hidden) return;
    if (!lastFrameAt || timestamp - lastFrameAt >= 1000 / 30) {
      draw(timestamp);
      lastFrameAt = timestamp;
    }
    frameId = window.requestAnimationFrame(animate);
  }

  if (!setupWebGL()) {
    if (!gl) console.warn('[birthday-card:03] WebGL is unavailable; using Canvas 2D silk motion.');
    gl = null;
    context2d = canvas.getContext('2d');
    if (!context2d) {
      document.body.classList.add('silk-css-fallback');
    }
  }
  card.dataset.motionProfile = 'editorial';
  card.dataset.motionState = context2d || gl ? 'active' : 'css-fallback';
  canvas.dataset.motionMode = gl ? 'webgl' : context2d ? 'canvas-2d' : 'css';

  const onPointerMove = (event) => {
    pointer.x = (event.clientX / Math.max(window.innerWidth, 1)) * 2 - 1;
    pointer.y = 1 - (event.clientY / Math.max(window.innerHeight, 1)) * 2;
  };
  const onVisibilityChange = () => {
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    lastFrameAt = 0;
    if (!document.hidden && !reduceMotion) frameId = window.requestAnimationFrame(animate);
  };
  addListener(window, 'resize', resize, { passive: true });
  addListener(window, 'orientationchange', resize, { passive: true });
  if (window.visualViewport) addListener(window.visualViewport, 'resize', resize, { passive: true });
  if (desktopPointer && !reduceMotion) addListener(window, 'pointermove', onPointerMove, { passive: true });
  addListener(document, 'visibilitychange', onVisibilityChange);
  addListener(window, 'pagehide', () => {
    if (frameId) window.cancelAnimationFrame(frameId);
    cleanup.forEach((remove) => remove());
    if (gl && program) gl.deleteProgram(program);
    if (gl) gl.getExtension('WEBGL_lose_context')?.loseContext();
    window.clearTimeout(toastTimer);
    window.clearTimeout(buttonTimer);
  }, { once: true });

  resize();
  if (!reduceMotion && (context2d || gl)) {
    frameId = window.requestAnimationFrame(animate);
  }

  if (desktopPointer && !reduceMotion) {
    addListener(card, 'pointermove', (event) => {
      if (event.pointerType === 'touch') return;
      const bounds = card.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / Math.max(bounds.width, 1);
      const y = (event.clientY - bounds.top) / Math.max(bounds.height, 1);
      const rotateX = (0.5 - y) * 3;
      const rotateY = (x - 0.5) * 4;
      card.style.transform = `perspective(72rem) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    }, { passive: true });
    addListener(card, 'pointerleave', () => {
      card.style.transform = '';
    }, { passive: true });
  }

  let toastTimer = 0;
  let buttonTimer = 0;
  let liveRegion = document.getElementById('birthday-toast-region');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'birthday-toast-region';
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    document.body.append(liveRegion);
  }

  addListener(button, 'click', () => {
    window.clearTimeout(toastTimer);
    window.clearTimeout(buttonTimer);
    const toast = document.createElement('div');
    toast.className = 'birthday-toast';
    toast.textContent = 'Chúc mừng sinh nhật! Chúc một tuổi mới nhiều niềm vui.';
    liveRegion.replaceChildren(toast);
    button.classList.remove('is-cheers');
    void button.offsetWidth;
    button.classList.add('is-cheers');
    toastTimer = window.setTimeout(() => liveRegion.replaceChildren(), 2900);
    buttonTimer = window.setTimeout(() => button.classList.remove('is-cheers'), 600);
  });
})();
