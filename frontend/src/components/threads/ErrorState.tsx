import styles from './Threads.module.css';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className={styles.statusContainer}>
      <div className={styles.emptyIcon}>⚠️</div>
      <h3 className={styles.errorState}>{message}</h3>
      <button className="btn btn-secondary retryBtn" onClick={onRetry}>Try Again</button>
    </div>
  );
}
