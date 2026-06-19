import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './PerformanceDetailPage.module.css';

interface Props {
  submissionId: number;
  onBack: () => void;
}

export default function PerformanceDetailPage({ submissionId, onBack }: Props) {
  const [detailData, setDetailData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDetail();
  }, [submissionId]);

  const fetchDetail = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    try {
      setLoading(true);
      const res = await fetch(apiUrl(`/api/user/mock-history/${submissionId}/`), {
        headers: { 'Authorization': `Token ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDetailData(data);
      }
    } catch (err) {
      console.error("Failed to fetch submission detail", err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    if (m > 60) {
      const h = Math.floor(m / 60);
      return `${h}h ${m % 60}m`;
    }
    return `${m}m ${s}s`;
  };

  if (loading || !detailData) {
    return (
      <div className={styles.wrapper}>
        <header className={styles.header}>
          <div className={`container ${styles.headerInner}`}>
            <button className="btn" onClick={onBack}>← Back to Analytics</button>
            <div className={styles.logo}>Mock Test Review</div>
            <div style={{ width: '150px' }}></div>
          </div>
        </header>
        <div style={{ textAlign: 'center', padding: '4rem' }}>Loading test review...</div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          <button className="btn" onClick={onBack}>← Back to Analytics</button>
          <div className={styles.logo}>Mock Test Review</div>
          <div style={{ width: '150px' }}></div>
        </div>
      </header>

      <main className="container">
        <div className={styles.pageHeader}>
          <h1 className={styles.title}>{detailData.track_title} Mock Test</h1>
          <p className={styles.subtitle}>
            Topic: {detailData.quiz_topic} • Submitted on {new Date(detailData.submitted_at).toLocaleString()}
          </p>
        </div>

        <div className={styles.detailStatsGrid}>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Score</div>
            <div className={styles.detailStatVal}>{detailData.score} / {detailData.max_score}</div>
          </div>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Percentage</div>
            <div className={styles.detailStatVal}>{detailData.percentage}%</div>
          </div>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Attempted</div>
            <div className={styles.detailStatVal}>{detailData.attempted} / {detailData.total_questions}</div>
          </div>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Accuracy</div>
            <div className={styles.detailStatVal}>{detailData.accuracy}%</div>
          </div>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Time Taken</div>
            <div className={styles.detailStatVal}>{formatTime(detailData.time_taken_seconds)}</div>
          </div>
          <div className={styles.detailStatBox}>
            <div className={styles.detailStatLabel}>Rank</div>
            <div className={styles.detailStatVal}>#{detailData.rank}</div>
          </div>
        </div>

        <h2 className={styles.questionsHeader}>Question by Question Review</h2>
        <div className={styles.questionsList}>
          {detailData.detailed_questions.map((q: any, idx: number) => {
            let statusClass = styles.questionItemSkipped;
            let statusText = "Skipped";
            let statusColorClass = styles.qStatusSkipped;
            
            if (q.user_answer) {
              if (q.is_correct) {
                statusClass = styles.questionItemCorrect;
                statusText = `Correct (+${q.marks_awarded})`;
                statusColorClass = styles.qStatusCorrect;
              } else {
                statusClass = styles.questionItemIncorrect;
                statusText = `Incorrect (${q.marks_awarded})`;
                statusColorClass = styles.qStatusIncorrect;
              }
            }

            return (
              <div key={q.id} className={`${styles.questionItem} ${statusClass}`}>
                <div className={styles.qHeader}>
                  <span className={styles.qNum}>Question {idx + 1}</span>
                  <span className={`${styles.qStatus} ${statusColorClass}`}>{statusText}</span>
                </div>
                <div className={styles.qText}>{q.text}</div>
                
                <div className={styles.optionsGrid}>
                  {['A', 'B', 'C', 'D'].map((letter, oIdx) => {
                    const optText = Array.isArray(q.options) 
                      ? q.options[oIdx] 
                      : (q.options ? q.options[letter] : `Option ${letter}`);
                    
                    const isCorrectAnswer = letter === q.correct_answer;
                    const isUserAnswer = letter === q.user_answer;
                    
                    let optClass = '';
                    if (isCorrectAnswer) optClass = styles.optionCorrect;
                    else if (isUserAnswer && !isCorrectAnswer) optClass = styles.optionUserWrong;
                    
                    return (
                      <div key={oIdx} className={`${styles.optionItem} ${optClass}`}>
                        <span className={styles.optionLabel}>{letter})</span>
                        <span>{optText}</span>
                        {isCorrectAnswer && <span style={{marginLeft:'auto'}}>✅</span>}
                        {isUserAnswer && !isCorrectAnswer && <span style={{marginLeft:'auto'}}>❌</span>}
                      </div>
                    );
                  })}
                </div>
                
                {q.explanation && (
                  <div className={styles.explanationBox}>
                    <h4>Explanation</h4>
                    <p>{q.explanation}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
