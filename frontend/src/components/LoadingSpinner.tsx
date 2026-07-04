interface Props {
  /** 'full' fills the viewport; 'inline' sits in-flow. Default: 'inline' */
  variant?: 'full' | 'inline'
  label?: string
}

export default function LoadingSpinner({
  variant = 'inline',
  label = 'Loading…',
}: Props) {
  if (variant === 'full') {
    return (
      <div className="spinner-full" role="status" aria-label={label}>
        <div className="spinner" />
        <span className="spinner-label">{label}</span>
      </div>
    )
  }

  return (
    <div className="spinner-wrap" role="status" aria-label={label}>
      <div className="spinner spinner--sm" />
    </div>
  )
}
