import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './DailyQuizHero.module.css';

interface QuizData {
  id: number;
  topic: string;
  track: string | null;
  track_slug: string | null;
  stage_name: string;
  date: string;
  starts_at: string | null;
  ends_at: string | null;
  duration_seconds: number;
  total_marks: number;
  marks_per_question: number;
  negative_marking: number;
  is_registered: boolean;
}

interface Props {
  onStartQuiz: (quizId: number) => void;
}

export default function DailyQuizHero({ onStartQuiz }: Props) {
  const [quizzes, setQuizzes] = useState<QuizData[]>([]);
  const [loading, setLoading] = useState(true);

  // Force flag for testing
  const FORCE_LIVE = new URLSearchParams(window.location.search).get('force') === 'true';

  useEffect(() => {
    fetchTodayQuizzes();
  }, []);

  const fetchTodayQuizzes = async () => {
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl('/api/quiz/today/'), {
        headers: token ? { 'Authorization': `Token ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setQuizzes(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error("Failed to fetch quizzes", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (quizId: number) => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      alert("Please login to register.");
      return;
    }
    try {
      const res = await fetch(apiUrl(`/api/quiz/${quizId}/register/`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`
        }
      });
      if (res.ok) {
        setQuizzes(prev => prev.map(q => q.id === quizId ? { ...q, is_registered: true } : q));
        alert("Successfully registered for this mock test!");
      } else {
        alert("Registration failed. Please try again.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };

  const isLive = (startsAt: string | null, endsAt: string | null) => {
    if (FORCE_LIVE) return true;
    if (!startsAt || !endsAt) return false;
    const now = new Date().getTime();
    return now >= new Date(startsAt).getTime() && now <= new Date(endsAt).getTime();
  };

  const isUpcoming = (startsAt: string | null) => {
    if (FORCE_LIVE) return false;
    if (!startsAt) return false;
    return new Date().getTime() < new Date(startsAt).getTime();
  };

  if (loading || quizzes.length === 0) {
    return null;
  }

  return (
    <div className={styles.gridSection}>
      <div className={styles.gridHeader}>
        <h2 className={styles.gridTitle}>Daily Mock Tests</h2>
        <p className={styles.gridSubtitle}>Select your exact learning path. You must register individually for the exams you wish to take.</p>
      </div>

      <div className={styles.cardsGrid}>
        {quizzes.map((quiz) => {
          const live = isLive(quiz.starts_at, quiz.ends_at);
          const upcoming = isUpcoming(quiz.starts_at);
          
          return (
            <div key={quiz.id} className={styles.quizCard}>
              <div className={styles.cardHeader}>
                <span className={styles.cardTrack}>{quiz.track || 'General'} - {quiz.stage_name}</span>
              </div>
              <div className={styles.cardBody}>
                <h3 className={styles.cardTopic}>{quiz.topic}</h3>
                <div className={styles.cardMeta} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1rem', fontSize: '0.9rem', color: '#555' }}>
                  <div><strong>Duration:</strong> {Math.floor(quiz.duration_seconds / 60)} Mins</div>
                  <div><strong>Scoring:</strong> +{quiz.marks_per_question} / -{quiz.negative_marking}</div>
                  <div>
                    <strong>Window:</strong>{' '}
                    {quiz.starts_at ? new Date(quiz.starts_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'TBD'} 
                    {' - '} 
                    {quiz.ends_at ? new Date(quiz.ends_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'TBD'}
                  </div>
                </div>
              </div>
              <div className={styles.cardFooter}>
                {!quiz.is_registered ? (
                  <button 
                    className={styles.registerBtnSmall} 
                    onClick={() => handleRegister(quiz.id)}
                  >
                    Register Free
                  </button>
                ) : (
                  live ? (
                    <button 
                      className={styles.startBtnSmall} 
                      onClick={() => onStartQuiz(quiz.id)}
                    >
                      Start Mock Test
                    </button>
                  ) : (
                    <button className={`${styles.startBtnSmall} ${styles.disabled}`} disabled>
                      {upcoming ? 'Starts Soon...' : 'Exam Closed'}
                    </button>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
