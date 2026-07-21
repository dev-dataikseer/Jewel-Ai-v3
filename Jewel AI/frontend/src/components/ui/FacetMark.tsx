type FacetMarkProps = {
  variant?: "outline" | "spin" | "check";
  className?: string;
  size?: number;
  title?: string;
};

/** Signature faceted-gem mark — use only for loading / empty / success. */
export function FacetMark({
  variant = "outline",
  className = "",
  size = 40,
  title,
}: FacetMarkProps) {
  const stroke = "currentColor";
  const spinClass = variant === "spin" ? "animate-facet-spin" : "";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${spinClass} ${className}`.trim()}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
    >
      {title ? <title>{title}</title> : null}
      {/* Outer diamond */}
      <path
        d="M20 3.5 L34 16.5 L20 36.5 L6 16.5 Z"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        fill={variant === "check" ? "color-mix(in srgb, var(--jewel-success) 12%, transparent)" : "none"}
      />
      {/* Crown facets */}
      <path d="M20 3.5 L26 16.5 L14 16.5 Z" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" fill="none" />
      <path d="M6 16.5 L14 16.5 L20 36.5" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" fill="none" />
      <path d="M34 16.5 L26 16.5 L20 36.5" stroke={stroke} strokeWidth="1.2" strokeLinejoin="round" fill="none" />
      <path d="M14 16.5 H26" stroke={stroke} strokeWidth="1.2" />
      {variant === "check" && (
        <path
          d="M14 20 L18 24 L26.5 14.5"
          stroke="var(--jewel-success)"
          strokeWidth="2"
          strokeLinecap="square"
          strokeLinejoin="miter"
          fill="none"
        />
      )}
      {variant === "spin" && (
        <path
          d="M20 3.5 L26 16.5"
          stroke="var(--jewel-accent)"
          strokeWidth="2"
          strokeLinecap="square"
        />
      )}
    </svg>
  );
}
