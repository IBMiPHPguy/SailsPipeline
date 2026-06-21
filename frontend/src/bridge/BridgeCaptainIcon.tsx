type BridgeCaptainIconProps = {
  className?: string;
  size?: number;
};

export default function BridgeCaptainIcon({ className, size = 72 }: BridgeCaptainIconProps) {
  return (
    <span
      className={`bridge-captain-icon${className ? ` ${className}` : ""}`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path
          d="M18 24c0-6 6.3-11 14-11s14 5 14 11"
          fill="currentColor"
          stroke="none"
        />
        <path d="M18 24h28" />
        <rect x="22" y="12" width="20" height="4" rx="1" fill="currentColor" stroke="none" />
        <circle cx="32" cy="38" r="18" />
        <circle cx="32" cy="38" r="4.5" fill="currentColor" stroke="none" />
        <path d="M32 20v6M32 50v6M14 38h6M44 38h6" />
        <path d="M19.8 25.8l4.2 4.2M44.2 50.2l4.2 4.2M44.2 25.8l-4.2 4.2M19.8 50.2l4.2-4.2" />
      </svg>
    </span>
  );
}
