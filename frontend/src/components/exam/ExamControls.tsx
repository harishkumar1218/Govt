import styles from './ExamComponents.module.css';

interface Props {
  onClear: () => void;
  onReview: () => void;
  onSaveNext: () => void;
  isLast: boolean;
}

export default function ExamControls({ onClear, onReview, onSaveNext, isLast }: Props) {
  return (
    <div className={styles.controlsBar}>
      <div className={styles.controlsLeft}>
        <button className="btn btn-outline" onClick={onClear}>Clear Response</button>
        <button className={`btn ${styles.btnReview}`} onClick={onReview}>Mark for Review & Next</button>
      </div>
      <div className={styles.controlsRight}>
        <button className="btn btn-primary" onClick={onSaveNext}>
          {isLast ? 'Save' : 'Save & Next'}
        </button>
      </div>
    </div>
  );
}
