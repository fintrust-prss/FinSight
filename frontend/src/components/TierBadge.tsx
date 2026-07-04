import type { Tier } from '../api/portfolio'

const TIER_META: Record<
  Tier,
  { className: string; label: string; shortLabel: string }
> = {
  Disciplined: {
    className: 'tier-badge--disciplined',
    label: 'Disciplined',
    shortLabel: 'D',
  },
  'Moderately Disciplined': {
    className: 'tier-badge--moderate',
    label: 'Moderately Disciplined',
    shortLabel: 'MD',
  },
  'Non-Disciplined': {
    className: 'tier-badge--review',
    label: 'Non-Disciplined',
    shortLabel: 'ND',
  },
  'No-Go': {
    className: 'tier-badge--nogo',
    label: 'No-Go',
    shortLabel: 'NG',
  },
}

interface Props {
  tier: Tier | string
  /** Show short label (for compact table cells). Default false */
  compact?: boolean
}

export default function TierBadge({ tier, compact = false }: Props) {
  const meta = TIER_META[tier as Tier] ?? {
    className: 'tier-badge--review',
    label: tier,
    shortLabel: tier.slice(0, 2).toUpperCase(),
  }

  return (
    <span
      className={`tier-badge ${meta.className}`}
      role="status"
      aria-label={`Decision tier: ${meta.label}`}
      title={meta.label}
    >
      {compact ? meta.shortLabel : meta.label}
    </span>
  )
}

/** CSS colour value for a given tier — for Recharts fill props */
export function tierColor(tier: Tier | string): string {
  switch (tier) {
    case 'Disciplined':
      return 'var(--color-tier-disciplined)'
    case 'Moderately Disciplined':
      return 'var(--color-tier-moderate)'
    case 'Non-Disciplined':
      return 'var(--color-tier-review)'
    case 'No-Go':
      return 'var(--color-tier-nogo)'
    default:
      return 'var(--color-text-muted)'
  }
}

/** Hex values for Recharts (which can't read CSS vars in SVG fills) */
export function tierHex(tier: Tier | string): string {
  switch (tier) {
    case 'Disciplined':
      return '#10b981'
    case 'Moderately Disciplined':
      return '#f59e0b'
    case 'Non-Disciplined':
      return '#f97316'
    case 'No-Go':
      return '#ef4444'
    default:
      return '#475569'
  }
}
