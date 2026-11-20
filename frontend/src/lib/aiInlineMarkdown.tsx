import type { ReactNode } from 'react';
import { getSafeAiLinkTarget } from './aiSafeLink';

const MAX_INLINE_DEPTH = 4;

/**
 * Locate the matching closing `*`, `**`, or `***` delimiter while skipping
 * inline code spans and tracking nested emphasis markers so patterns such as
 * `*Gợi ý tại **[Kho Tài Liệu & Biểu Mẫu](/resources)**.*` close accurately.
 */
function findClosingStars(text: string, start: number, markerLen: 1 | 2 | 3): number {
  let pos = start;
  let nestedBoldOpen = false;
  let nestedItalicOpen = false;

  while (pos < text.length) {
    if (text[pos] === '`') {
      const codeClose = text.indexOf('`', pos + 1);
      pos = codeClose !== -1 ? codeClose + 1 : pos + 1;
      continue;
    }

    if (text[pos] !== '*') {
      pos += 1;
      continue;
    }

    let runEnd = pos;
    while (runEnd < text.length && text[runEnd] === '*') {
      runEnd += 1;
    }
    const runLen = runEnd - pos;

    if (markerLen === 1) {
      if (runLen === 2) {
        nestedBoldOpen = !nestedBoldOpen;
      } else if (runLen === 1) {
        if (pos > start && !/\s/.test(text[pos - 1])) {
          return pos;
        }
      } else if (runLen >= 3) {
        if (nestedBoldOpen) {
          return pos + 2;
        }
        if (pos > start && !/\s/.test(text[pos - 1])) {
          return pos;
        }
      }
    } else if (markerLen === 2) {
      if (runLen === 1) {
        nestedItalicOpen = !nestedItalicOpen;
      } else if (runLen === 2 && pos > start) {
        return pos;
      } else if (runLen >= 3 && pos > start) {
        return nestedItalicOpen ? pos + 1 : pos;
      }
    } else if (runLen >= 3 && pos > start) {
      return pos;
    }

    pos = runEnd;
  }

  return -1;
}

/**
 * Render a safe inline Markdown subset (code, inline math, links constrained by
 * `getSafeAiLinkTarget`, and nested emphasis) into React nodes with raw HTML escaped.
 */
export function renderAiInlineMarkdown(
  text: string = '',
  keyPrefix: string = 'inline',
  onInternalLink?: (href: string) => void,
  depth: number = 0,
): ReactNode[] {
  if (!text) {
    return [text];
  }

  const nodes: ReactNode[] = [];
  let plain = '';
  let i = 0;

  const flushPlain = () => {
    if (plain) {
      nodes.push(plain);
      plain = '';
    }
  };

  while (i < text.length) {
    if (text[i] === '`') {
      const close = text.indexOf('`', i + 1);
      if (close > i + 1) {
        flushPlain();
        nodes.push(
          <code key={`${keyPrefix}-code-${i}`} className="rounded bg-surface-hover px-1">
            {text.slice(i + 1, close)}
          </code>,
        );
        i = close + 1;
        continue;
      }
    }

    if (text[i] === '$') {
      const mathMatch = /^\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/.exec(text.slice(i));
      if (mathMatch) {
        flushPlain();
        nodes.push(
          <code key={`${keyPrefix}-math-${i}`} className="ai-math-inline">
            {mathMatch[1]}
          </code>,
        );
        i += mathMatch[0].length;
        continue;
      }
    }

    if (text[i] === '[') {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)/.exec(text.slice(i));
      if (linkMatch) {
        flushPlain();
        const rawLabel = linkMatch[1];
        const safeHref = getSafeAiLinkTarget(linkMatch[2].trim());
        const renderedLabel =
          depth < MAX_INLINE_DEPTH
            ? renderAiInlineMarkdown(rawLabel, `${keyPrefix}-l${i}`, onInternalLink, depth + 1)
            : [rawLabel];

        if (safeHref) {
          nodes.push(
            <a
              key={`${keyPrefix}-a-${i}`}
              href={safeHref}
              className="text-primary underline"
              onClick={
                onInternalLink
                  ? (event) => {
                      event.preventDefault();
                      onInternalLink(safeHref);
                    }
                  : undefined
              }
            >
              {renderedLabel}
            </a>,
          );
        } else {
          nodes.push(...renderedLabel);
        }
        i += linkMatch[0].length;
        continue;
      }
    }

    if (depth < MAX_INLINE_DEPTH && text[i] === '*') {
      if (text.startsWith('***', i)) {
        const close = findClosingStars(text, i + 3, 3);
        const inner = close > i + 3 ? text.slice(i + 3, close) : '';
        if (close > i + 3 && inner.trim().length > 0) {
          flushPlain();
          nodes.push(
            <strong key={`${keyPrefix}-be-${i}`}>
              <em>
                {renderAiInlineMarkdown(inner, `${keyPrefix}-be${i}`, onInternalLink, depth + 1)}
              </em>
            </strong>,
          );
          i = close + 3;
          continue;
        }
      }

      if (text.startsWith('**', i)) {
        const close = findClosingStars(text, i + 2, 2);
        const inner = close > i + 2 ? text.slice(i + 2, close) : '';
        if (close > i + 2 && inner.trim().length > 0) {
          flushPlain();
          nodes.push(
            <strong key={`${keyPrefix}-b-${i}`}>
              {renderAiInlineMarkdown(inner, `${keyPrefix}-b${i}`, onInternalLink, depth + 1)}
            </strong>,
          );
          i = close + 2;
          continue;
        }
      }

      if (i + 1 < text.length && text[i + 1] !== '*' && !/\s/.test(text[i + 1])) {
        const close = findClosingStars(text, i + 1, 1);
        const inner = close > i + 1 ? text.slice(i + 1, close) : '';
        if (close > i + 1 && inner.trim().length > 0) {
          flushPlain();
          nodes.push(
            <em key={`${keyPrefix}-em-${i}`}>
              {renderAiInlineMarkdown(inner, `${keyPrefix}-em${i}`, onInternalLink, depth + 1)}
            </em>,
          );
          i = close + 1;
          continue;
        }
      }
    }

    plain += text[i];
    i += 1;
  }

  flushPlain();
  return nodes.length > 0 ? nodes : [text];
}
