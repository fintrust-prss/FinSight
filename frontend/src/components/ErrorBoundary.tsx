interface ErrorCardProps {
  title?: string
  message?: string
  onRetry?: () => void
}

export function ErrorCard({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorCardProps) {
  return (
    <div className="error-card" role="alert">
      <span className="error-card__icon" aria-hidden="true">⚠</span>
      <h3 className="error-card__title">{title}</h3>
      {message && <p className="error-card__message">{message}</p>}
      {onRetry && (
        <button id="btn-retry" className="btn btn--primary btn--sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
}

export function EmptyState({ icon = '○', title, description }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon" aria-hidden="true">{icon}</span>
      <h3 className="empty-state__title">{title}</h3>
      {description && <p className="empty-state__desc">{description}</p>}
    </div>
  )
}
