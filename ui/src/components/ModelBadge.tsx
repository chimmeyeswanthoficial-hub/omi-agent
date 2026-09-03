export default function ModelBadge({ group, provider }: { group: string; provider: string }) {
  return (
    <span title={`omirouter routed this call to provider '${provider}' (task group: ${group})`} className="text-[10px] px-1.5 py-0 rounded-full border border-edge text-mut">
      max → {provider}
      <span className="text-mut/60"> · {group}</span>
    </span>
  );
}
