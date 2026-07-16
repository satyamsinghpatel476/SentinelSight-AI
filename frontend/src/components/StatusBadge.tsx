type StatusBadgeProps = {
  label: string;
  tone: "good" | "pending" | "blocked";
};

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}
