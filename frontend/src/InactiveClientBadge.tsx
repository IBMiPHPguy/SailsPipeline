type InactiveClientBadgeProps = {
  className?: string;
};

export default function InactiveClientBadge({ className = "" }: InactiveClientBadgeProps) {
  return <span className={`inactive-client-badge${className ? ` ${className}` : ""}`}>Inactive client</span>;
}
