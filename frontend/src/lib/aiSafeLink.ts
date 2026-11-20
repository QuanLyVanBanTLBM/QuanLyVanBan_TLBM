const ALLOWED_AI_INTERNAL_ROUTE_PREFIXES = [
  '/dashboard',
  '/documents',
  '/records',
  '/resources',
  '/approvals',
  '/tasks',
  '/organizations',
  '/ai-assistant',
  '/employees',
  '/birthdays',
];

export function getSafeAiLinkTarget(href: string | undefined): string | null {
  if (!href || !href.startsWith('/') || href.startsWith('//')) {
    return null;
  }
  const pathname = href.split(/[?#]/, 1)[0] || '/';
  const isAllowed = ALLOWED_AI_INTERNAL_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  return isAllowed ? href : null;
}
