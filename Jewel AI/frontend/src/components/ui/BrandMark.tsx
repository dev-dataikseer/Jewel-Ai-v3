/** Faceted diamond logomark — brand gradient tile. */
export function BrandMark({
  size = 36,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#4F46E5" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="10" fill="url(#brandGrad)" />
      <path
        d="M20 8 L30 16.5 L20 32 L10 16.5 Z"
        stroke="white"
        strokeWidth="1.5"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M20 8 L24.5 16.5 L15.5 16.5 Z" stroke="white" strokeWidth="1.1" fill="none" />
      <path d="M15.5 16.5 H24.5" stroke="white" strokeWidth="1.1" />
      <path d="M10 16.5 L15.5 16.5 L20 32" stroke="white" strokeWidth="1" opacity="0.85" fill="none" />
      <path d="M30 16.5 L24.5 16.5 L20 32" stroke="white" strokeWidth="1" opacity="0.85" fill="none" />
    </svg>
  );
}
