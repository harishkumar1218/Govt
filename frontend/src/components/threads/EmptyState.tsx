import styles from './Threads.module.css';

interface EmptyStateProps {
  isSearch?: boolean;
  onAskDoubtClick?: () => void;
}

export default function EmptyState({ isSearch = false, onAskDoubtClick }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>{isSearch ? '🔍' : '📚'}</div>
      <h3>{isSearch ? 'No matching doubts found' : 'No doubts posted yet'}</h3>
      <p>
        {isSearch 
          ? 'Try adjusting your search terms, sort, or category filters.'
          : 'Ask the first question and start the discussion.'}
      </p>
      {!isSearch && onAskDoubtClick && (
        <button
          className="btn btn-primary"
          style={{ marginTop: '0.75rem' }}
          onClick={onAskDoubtClick}
          aria-label="Ask first doubt"
        >
          Ask Doubt
        </button>
      )}
    </div>
  );
}
