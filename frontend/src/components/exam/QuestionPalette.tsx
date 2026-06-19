import type { Question } from '../../data/mockQuestions';
import type { QuestionStatus } from '../../pages/ExamPage';
import styles from './ExamComponents.module.css';

interface Props {
  questions: Question[];
  currentIndex: number;
  statusMap: Record<number, QuestionStatus>;
  onJump: (index: number) => void;
}

export default function QuestionPalette({ questions, currentIndex, statusMap, onJump }: Props) {
  const getStatusClass = (status: QuestionStatus) => {
    switch(status) {
      case 'answered': return styles.bubbleAnswered;
      case 'unanswered': return styles.bubbleUnanswered;
      case 'marked': return styles.bubbleMarked;
      default: return '';
    }
  };

  return (
    <div className={styles.paletteContainer}>
      <div className={styles.paletteHeader}>
        <h3>Question Palette</h3>
      </div>
      <div className={styles.legendContainer}>
        <div className={styles.legendItem}>
          <span className={`${styles.legendBubble} ${styles.bubbleAnswered}`}></span> Answered
        </div>
        <div className={styles.legendItem}>
          <span className={`${styles.legendBubble} ${styles.bubbleUnanswered}`}></span> Not Answered
        </div>
        <div className={styles.legendItem}>
          <span className={`${styles.legendBubble} ${styles.bubbleMarked}`}></span> Marked
        </div>
        <div className={styles.legendItem}>
          <span className={styles.legendBubble}></span> Not Visited
        </div>
      </div>
      <div className={styles.grid}>
        {questions.map((q, idx) => {
          const status = statusMap[q.id] || 'unvisited';
          const isActive = currentIndex === idx;
          return (
            <button
              key={q.id}
              className={`${styles.bubble} ${getStatusClass(status)} ${isActive ? styles.bubbleActive : ''}`}
              onClick={() => onJump(idx)}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}
