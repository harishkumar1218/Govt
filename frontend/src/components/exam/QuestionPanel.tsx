import type { Question } from '../../data/mockQuestions';
import styles from './ExamComponents.module.css';

interface Props {
  question: Question;
  index: number;
  selectedOption?: number;
  onSelect: (index: number) => void;
}

export default function QuestionPanel({ question, index, selectedOption, onSelect }: Props) {
  return (
    <div className={styles.questionPanel}>
      <div className={styles.questionHeader}>
        <span className={styles.qNum}>Question {index}</span>
      </div>
      <div className={styles.questionText}>
        {question.text.split('\n').map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>
      <div className={styles.optionsList}>
        {question.options.map((opt, idx) => (
          <label 
            key={idx} 
            className={`${styles.optionLabel} ${selectedOption === idx ? styles.optionSelected : ''}`}
          >
            <div className={styles.radioWrapper}>
              <input 
                type="radio" 
                name={`question-${question.id}`} 
                checked={selectedOption === idx}
                onChange={() => onSelect(idx)}
              />
            </div>
            <span className={styles.optionText}>{opt}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
