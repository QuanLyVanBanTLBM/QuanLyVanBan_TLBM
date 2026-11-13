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

const layouts = Array.from({ length: 10 }, (_, index) => String(index + 1).padStart(2, '0'));

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
    expect(html).toMatch(/<button\b/);

    if (layout === '03') {
      expect(html).toContain('/birthday-cards/motion-03.js');
      expect(html).not.toContain('/birthday-cards/motion.js');
    } else {
      expect(html).toContain('/birthday-cards/motion.js');
      expect(html).toContain('three.min.js');
      expect(html).toContain('gsap.min.js');
      expect(html).toContain('confetti.browser.min.js');
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

  it('keeps the card interaction usable and announces it to assistive technology', () => {
    document.body.innerHTML = '<canvas id="bgWebGL"></canvas><article data-birthday-card="01"><button id="celebrate">Mở lời chúc</button><div id="candleFlames"></div></article>';
    const gsap = { from: vi.fn(), fromTo: vi.fn(), to: vi.fn() };
    const confetti = vi.fn();
    vi.stubGlobal('gsap', gsap);
    vi.stubGlobal('confetti', confetti);

    new Function(readFileSync(resolve(cardDirectory, 'motion.js'), 'utf8'))();
    document.querySelector<HTMLButtonElement>('#celebrate')?.click();

    const button = document.querySelector('#celebrate');
    const status = document.querySelector('[role="status"]');
    expect(button).toHaveAttribute('aria-pressed', 'true');
    expect(status).toHaveAttribute('aria-live', 'polite');
    expect(status).toHaveTextContent('Chúc mừng sinh nhật');
    expect(document.querySelector('#candleFlames')).toHaveClass('blown');
    expect(confetti).toHaveBeenCalledOnce();
    expect(gsap.fromTo).toHaveBeenCalledOnce();
  });
});
