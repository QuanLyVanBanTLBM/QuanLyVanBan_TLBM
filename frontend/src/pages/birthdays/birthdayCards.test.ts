/// <reference types="node" />
/// <reference types="vitest/globals" />

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, vi } from 'vitest';
import { waitFor } from '@testing-library/react';

const cardDirectory = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../../public/birthday-cards',
);
const repositoryRoot = resolve(cardDirectory, '../../..');

const layouts = Array.from({ length: 10 }, (_, index) => String(index + 1).padStart(2, '0'));
const createCanvasContext = () => ({
  clearRect: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  translate: vi.fn(),
  rotate: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  quadraticCurveTo: vi.fn(),
  arc: vi.fn(),
  closePath: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  setTransform: vi.fn(),
  createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
}) as unknown as CanvasRenderingContext2D;

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = '';
  window.history.replaceState(null, '', '/');
});

describe('public birthday card layouts', () => {
  it.each(layouts)('keeps layout %s mapped to its personalized interactive page', (layout) => {
    const html = readFileSync(resolve(cardDirectory, `${layout}.html`), 'utf8');

    expect(html).toContain(`data-birthday-card="${layout}"`);
    expect(html).toContain('/birthday-cards/personalize.js');
    expect(html).toContain('data-card-field="job_title"');
    expect(html).toContain('min-height: 100dvh;');
    expect(html).toMatch(/<button\b/);
    const scriptTags = [...html.matchAll(/<script\b([^>]*)>/g)].map(([, attributes]) => attributes);
    const runtimeName = layout === '03' ? 'motion-03.js' : 'motion.js';
    const runtimeTag = scriptTags.find((attributes) => attributes.includes(runtimeName));
    expect(runtimeTag).toContain('defer');
    expect(readFileSync(resolve(cardDirectory, runtimeName), 'utf8')).toContain('prefers-reduced-motion: reduce');

    if (layout === '03') {
      expect(html).toContain('/birthday-cards/motion-03.js');
      expect(html).not.toContain('/birthday-cards/motion.js');
    } else {
      expect(html).toContain('/birthday-cards/motion.js');
      const dependencyNames = ['three.min.js', 'gsap.min.js', 'confetti.browser.min.js'];
      const dependencyIndexes = dependencyNames.map((name) => {
        const index = scriptTags.findIndex((attributes) => attributes.includes(name));
        expect(index).toBeGreaterThanOrEqual(0);
        expect(scriptTags[index]).toContain('defer');
        return index;
      });
      expect(dependencyIndexes[0]).toBeLessThan(scriptTags.indexOf(runtimeTag!));
      expect(dependencyIndexes[1]).toBeLessThan(scriptTags.indexOf(runtimeTag!));
      expect(dependencyIndexes[2]).toBeLessThan(scriptTags.indexOf(runtimeTag!));
    }
  });

  it('hides empty optional fields when a layout assigns display styles', async () => {
    document.body.innerHTML = '<small data-card-optional="job_title" hidden style="display: block"><span data-card-field="job_title"></span></small>';
    window.history.replaceState(null, '', '/birthday-cards/01.html#token=test-token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ card: { job_title: '' } }),
    }));

    new Function(readFileSync(resolve(cardDirectory, 'personalize.js'), 'utf8'))();
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const optionalField = document.querySelector<HTMLElement>('[data-card-optional="job_title"]');
    await waitFor(() => expect(optionalField?.style.display).toBe('none'));
    expect(optionalField).toHaveAttribute('hidden');
  });

  it('keeps optional fields hidden before a token or API response is available', () => {
    document.body.innerHTML = '<small data-card-optional="job_title" hidden style="display: block"><span data-card-field="job_title"></span></small>';
    window.history.replaceState(null, '', '/birthday-cards/01.html');

    new Function(readFileSync(resolve(cardDirectory, 'personalize.js'), 'utf8'))();

    const optionalField = document.querySelector<HTMLElement>('[data-card-optional="job_title"]');
    expect(window.getComputedStyle(optionalField!).display).toBe('none');
  });

  it('keeps the card interaction usable and announces it to assistive technology', () => {
    document.body.innerHTML = '<canvas id="bgWebGL"></canvas><article data-birthday-card="01"><button id="celebrate">Mở lời chúc</button><div id="candleFlames"></div></article>';
    const gsap = { from: vi.fn(), fromTo: vi.fn(), to: vi.fn() };
    const confetti = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createCanvasContext());
    vi.stubGlobal('gsap', gsap);
    vi.stubGlobal('confetti', confetti);

    new Function(readFileSync(resolve(cardDirectory, 'motion.js'), 'utf8'))();
    document.querySelector<HTMLButtonElement>('#celebrate')?.click();

    const button = document.querySelector('#celebrate');
    const status = document.querySelector('[role="status"]');
    expect(button).not.toHaveAttribute('aria-pressed');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveTextContent('Chúc mừng sinh nhật');
    expect(document.querySelector('#candleFlames')).toHaveClass('blown');
    expect(confetti).toHaveBeenCalledOnce();
    expect(gsap.fromTo).toHaveBeenCalledOnce();
  });

  it('runs an offline motion fallback with a profile for every shared-runtime layout', () => {
    const profiles: Record<string, string> = {
      '01': 'royal',
      '02': 'emerald',
      '04': 'ruby',
      '05': 'cyber',
      '06': 'botanical',
      '07': 'galaxy',
      '08': 'sunrise',
      '09': 'parchment',
      '10': 'party',
    };
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createCanvasContext());
    vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1));
    vi.stubGlobal('cancelAnimationFrame', vi.fn());

    for (const [layout, profile] of Object.entries(profiles)) {
      document.body.innerHTML = `<canvas id="background"></canvas><article data-birthday-card="${layout}"><button>Celebrate</button></article>`;
      new Function(readFileSync(resolve(cardDirectory, 'motion.js'), 'utf8'))();

      const card = document.querySelector<HTMLElement>('[data-birthday-card]');
      expect(card?.dataset.motionProfile).toBe(profile);
      expect(card?.dataset.motionState).toBe('active');
      expect(document.querySelector('canvas')?.dataset.motionMode).toBe('canvas-2d');
      window.dispatchEvent(new Event('pagehide'));
    }
  });

  it('keeps reduced-motion cards readable and their action available', () => {
    document.body.innerHTML = '<canvas id="background"></canvas><article data-birthday-card="01"><button id="celebrate">Celebrate</button><div id="candleFlames"></div></article>';
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }));
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createCanvasContext());
    const confetti = vi.fn();
    vi.stubGlobal('confetti', confetti);

    new Function(readFileSync(resolve(cardDirectory, 'motion.js'), 'utf8'))();
    document.querySelector<HTMLButtonElement>('#celebrate')?.click();

    expect(document.querySelector<HTMLElement>('[data-birthday-card]')?.dataset.motionState).toBe('active');
    expect(document.querySelector('[role="status"]')).toHaveTextContent('Chúc mừng sinh nhật');
    expect(confetti).not.toHaveBeenCalled();
  });

  it('keeps invalid-token status out of the card layout flow on narrow screens', async () => {
    document.body.innerHTML = '<main style="display:flex"><article data-birthday-card="01"></article></main>';
    window.history.replaceState(null, '', '/birthday-cards/01.html#token=invalid-token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 400 }));

    new Function(readFileSync(resolve(cardDirectory, 'personalize.js'), 'utf8'))();
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const status = await waitFor(() => {
      const element = document.querySelector<HTMLElement>('[data-card-status]');
      expect(element).not.toBeNull();
      expect(element?.style.position).toBe('fixed');
      return element;
    });
    expect(status?.style.width).toContain('100vw');
  });

  it('serves standalone card assets as files and never as the SPA fallback', () => {
    const nginx = readFileSync(resolve(repositoryRoot, 'deploy/nginx/qlvb-frontend.conf'), 'utf8');
    const locationStart = nginx.indexOf('location ^~ /birthday-cards/');
    const locationEnd = nginx.indexOf('\n    }', locationStart);
    const cardLocation = nginx.slice(locationStart, locationEnd);
    const spaFallback = nginx.indexOf('location / { try_files $uri $uri/ /index.html; }');

    expect(locationStart).toBeGreaterThanOrEqual(0);
    expect(cardLocation).toContain('try_files $uri =404;');
    expect(locationStart).toBeLessThan(spaFallback);
    expect(readFileSync(resolve(cardDirectory, 'motion.js'), 'utf8')).toContain("dataset.motionMode = 'canvas-2d'");
  });

  it('keeps the editorial layout animated and interactive without WebGL', () => {
    document.body.innerHTML = '<canvas id="silkCanvas"></canvas><article id="paperCard" data-birthday-card="03"><button id="toastBtn">Cheers</button></article>';
    const context = createCanvasContext();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation((type) => (
      type === 'webgl' ? null : context
    ));
    vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1));
    vi.stubGlobal('cancelAnimationFrame', vi.fn());

    new Function(readFileSync(resolve(cardDirectory, 'motion-03.js'), 'utf8'))();
    document.querySelector<HTMLButtonElement>('#toastBtn')?.click();

    expect(document.querySelector('#birthday-toast-region')).toHaveTextContent('Chúc mừng sinh nhật');
    expect(document.querySelector<HTMLElement>('#paperCard')?.dataset.motionProfile).toBe('editorial');
    expect(document.querySelector<HTMLElement>('#paperCard')?.dataset.motionState).toBe('active');
    expect(document.querySelector<HTMLCanvasElement>('#silkCanvas')?.dataset.motionMode).toBe('canvas-2d');
    window.dispatchEvent(new Event('pagehide'));
  });
});
