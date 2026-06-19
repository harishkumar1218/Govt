
import styles from './EssayRubricBreakdown.module.css';

interface RubricItem {
  criterion: string;
  score: number;
  max_score: number;
  reasoning: string;
  positive: string;
  negative: string;
  improvement: string;
}

interface Props {
  rubric: RubricItem[];
}

export default function EssayRubricBreakdown({ rubric }: Props) {
  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Detailed Rubric Breakdown</h3>
      <div className={styles.rubricList}>
        {rubric.map((item, idx) => {
          const percent = (item.score / item.max_score) * 100;
          return (
            <div key={idx} className={styles.rubricCard}>
              <div className={styles.rubricHeader}>
                <h4 className={styles.criterion}>{item.criterion}</h4>
                <div className={styles.scoreBadge}>
                  {item.score} / {item.max_score}
                </div>
              </div>
              
              <div className={styles.progressTrack}>
                <div 
                  className={styles.progressFill} 
                  style={{ width: `${percent}%`, backgroundColor: percent >= 70 ? 'var(--success)' : percent >= 40 ? '#f59e0b' : 'var(--danger)' }}
                ></div>
              </div>
              
              <p className={styles.reasoning}>{item.reasoning}</p>
              
              <div className={styles.feedbackGrid}>
                <div className={styles.feedbackBox}>
                  <strong className={styles.positiveLabel}>What Worked:</strong>
                  <span>{item.positive}</span>
                </div>
                <div className={styles.feedbackBox}>
                  <strong className={styles.negativeLabel}>Needs Work:</strong>
                  <span>{item.negative}</span>
                </div>
                <div className={`${styles.feedbackBox} ${styles.actionBox}`}>
                  <strong className={styles.actionLabel}>Action:</strong>
                  <span>{item.improvement}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
