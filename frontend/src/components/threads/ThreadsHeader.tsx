import styles from './Threads.module.css';

interface ThreadsHeaderProps {
  onNewPostClick: () => void;
}

export default function ThreadsHeader({ onNewPostClick }: ThreadsHeaderProps) {
  return (
    <div className={styles.threadsHeader}>
      <div className={styles.headerTitleSection}>
        <h1>Threads</h1>
        <p>Ask doubts, discuss concepts, and help other aspirants.</p>
      </div>
      <button
        className="btn btn-primary"
        onClick={onNewPostClick}
        id="btn-ask-doubt"
        aria-label="Ask a new doubt"
      >
        Ask Doubt
      </button>
    </div>
  );
}
