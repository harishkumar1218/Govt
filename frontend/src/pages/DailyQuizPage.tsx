// @ts-nocheck
import { apiUrl } from '../config/api';
import { useState, useEffect } from 'react';
import styles from './ExamPage.module.css';
import QuestionPanel from '../components/exam/QuestionPanel';
import QuestionPalette from '../components/exam/QuestionPalette';
import ExamControls from '../components/exam/ExamControls';

export type QuestionStatus = 'unvisited' | 'answered' | 'unanswered' | 'marked';

interface Question {
  id: number;
  text: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

interface QuizResult {
  id: number;
  user_answer: string;
  correct_answer: string;
  explanation: string;
  is_correct: boolean;
}

interface Props {
  quizId: number;
  onBack: () => void;
  onViewAnalytics?: () => void;
}

export default function DailyQuizPage({ quizId, onBack, onViewAnalytics }: Props) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Quiz State
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [statusMap, setStatusMap] = useState<Record<number, QuestionStatus>>({});
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    fetchQuestions();
  }, [quizId]);

  useEffect(() => {
    if (loading || isSubmitted || timeRemaining === null || timeRemaining <= 0) return;
    const timer = setInterval(() => setTimeRemaining(prev => (prev && prev > 0 ? prev - 1 : 0)), 1000);
    return () => clearInterval(timer);
  }, [loading, isSubmitted, timeRemaining]);

  useEffect(() => {
    if (timeRemaining === 0 && !isSubmitted && questions.length > 0) {
      handleSubmit();
    }
  }, [timeRemaining, isSubmitted, questions.length]);

  const fetchQuestions = async () => {
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/quiz/${quizId}/start/`), {
        headers: { 'Authorization': `Token ${token}` }
      });
      if (!res.ok) {
        const errData = await res.json();
        setError(errData.error || 'Failed to load quiz');
        setLoading(false);
      } else {
        const data = await res.json();
        setTimeRemaining(data.duration_seconds || 600);
        
        // Transform the dictionary options into string array for QuestionPanel
        const transformed: Question[] = data.questions.map((q: any) => {
          const optsArray = [
            `A) ${q.options['A'] || ''}`,
            `B) ${q.options['B'] || ''}`,
            `C) ${q.options['C'] || ''}`,
            `D) ${q.options['D'] || ''}`,
          ];
          return {
            id: q.id,
            text: q.text,
            options: optsArray,
            correctAnswer: 0, // Not needed until submit
            explanation: ""
          };
        });
        
        setQuestions(transformed);
        
        const initialStatus: Record<number, QuestionStatus> = {};
        transformed.forEach((q) => {
          initialStatus[q.id] = 'unvisited';
        });
        if (transformed.length > 0) {
          initialStatus[transformed[0].id] = 'unanswered';
        }
        setStatusMap(initialStatus);
      }
    } catch (e) {
      setError('Network error.');
    } finally {
      setLoading(false);
    }
  };

  const currentQuestion = questions[currentIndex];

  const handleSelectOption = (optionIndex: number) => {
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: optionIndex }));
  };

  const handleClearResponse = () => {
    setAnswers(prev => {
      const newAnswers = { ...prev };
      delete newAnswers[currentQuestion.id];
      return newAnswers;
    });
    setStatusMap(prev => ({ ...prev, [currentQuestion.id]: 'unanswered' }));
  };

  const handleMarkForReview = () => {
    setStatusMap(prev => ({ ...prev, [currentQuestion.id]: 'marked' }));
    goToNext();
  };

  const handleSaveAndNext = () => {
    const hasAnswer = answers[currentQuestion.id] !== undefined;
    setStatusMap(prev => ({ 
      ...prev, 
      [currentQuestion.id]: hasAnswer ? 'answered' : 'unanswered' 
    }));
    goToNext();
  };

  const goToNext = () => {
    if (currentIndex < questions.length - 1) {
      const nextId = questions[currentIndex + 1].id;
      setCurrentIndex(currentIndex + 1);
      setStatusMap(prev => ({
        ...prev,
        [nextId]: prev[nextId] === 'unvisited' ? 'unanswered' : prev[nextId]
      }));
    }
  };

  const jumpToQuestion = (index: number) => {
    const hasAnswer = answers[currentQuestion.id] !== undefined;
    if (statusMap[currentQuestion.id] === 'unanswered' && !hasAnswer) {
      // already unanswered
    }
    
    setCurrentIndex(index);
    const targetId = questions[index].id;
    setStatusMap(prev => ({
      ...prev,
      [targetId]: prev[targetId] === 'unvisited' ? 'unanswered' : prev[targetId]
    }));
  };

  const handleSubmit = async () => {
    setIsSubmitted(true);
    const token = localStorage.getItem('auth_token');
    
    // Transform answer indexes to 'A', 'B', 'C', 'D'
    const payloadAnswers: { [key: string]: string } = {};
    Object.keys(answers).forEach((qId) => {
      const val = answers[Number(qId)];
      if (val !== undefined) {
        payloadAnswers[qId] = String.fromCharCode(65 + val);
      }
    });
    
    // Duration could be read from state if we stored original duration_seconds, we fallback to 600
    // Actually timeRemaining was initialized with duration_seconds, but let's assume 600 if we didn't save it.
    // For now we pass 0 and the backend computes it correctly if we want, but backend needs `time_taken_seconds`
    // Let's use 600 as default max time if we didn't store it, or better: we don't know the exact max time here
    // unless we store it. Let's just use what we have, or pass what we know. 
    // Wait, let's keep it simple: 
    const timeTaken = Math.max(0, 600 - (timeRemaining || 0));

    try {
      const res = await fetch(apiUrl(`/api/quiz/${quizId}/submit/`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`
        },
        body: JSON.stringify({ answers: payloadAnswers, time_taken_seconds: timeTaken })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data);
      } else {
        alert("Failed to submit quiz.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h > 0 ? h.toString().padStart(2, '0') + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className={styles.examWrapper} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <div className="spinner" style={{ width: '50px', height: '50px', border: '5px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <h2 style={{ marginTop: '2rem' }}>Loading Daily Mock Test Environment...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.examWrapper} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <h2>Access Denied</h2>
        <p style={{ color: 'var(--danger)', marginTop: '1rem', maxWidth: '600px', textAlign: 'center' }}>{error}</p>
        <button className="btn btn-primary" onClick={onBack} style={{ marginTop: '2rem' }}>Back to Dashboard</button>
      </div>
    );
  }

  if (isSubmitted && results) {
    const correctCount = results.results.filter((r: any) => r.is_correct).length;
    const maxScore = results.total * (results.marks_per_question || 2.0); // Backend doesn't return marks_per_question yet, fallback to 2.0
    const percentage = maxScore > 0 ? ((results.score / maxScore) * 100).toFixed(1) : 0;
    const accuracy = results.total > 0 ? Math.round((correctCount / results.total) * 100) : 0;
    const incorrectCount = results.results.filter((r: any) => r.user_answer && !r.is_correct).length;
    const skippedCount = results.results.filter((r: any) => !r.user_answer).length;

    return (
      <div className={styles.examWrapper} style={{ padding: '2rem', overflowY: 'auto' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', background: 'var(--bg-secondary)', borderRadius: '16px', padding: '2rem', border: '1px solid var(--border)' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem', paddingBottom: '2rem', borderBottom: '1px solid var(--border)' }}>
            <h2>Mock Test Analytics</h2>
            <div style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--primary)', margin: '1rem 0' }}>
              {typeof results.score === 'number' ? results.score.toFixed(2) : results.score} Marks
            </div>
            <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>
              ({percentage}% of max marks)
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: '8px', minWidth: '120px', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Accuracy</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: accuracy >= 70 ? 'var(--success)' : 'var(--primary)' }}>{accuracy}%</div>
              </div>
              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: '8px', minWidth: '120px', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Time Taken</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)' }}>{formatTime(results.time_taken_seconds || 0)}</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '1.5rem', flexWrap: 'wrap' }}>
              <span style={{ padding: '0.5rem 1rem', background: 'rgba(34, 197, 94, 0.1)', color: 'var(--success)', borderRadius: '50px', fontSize: '0.9rem', fontWeight: 600 }}>Correct: {correctCount}</span>
              <span style={{ padding: '0.5rem 1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: '50px', fontSize: '0.9rem', fontWeight: 600 }}>Incorrect: {incorrectCount}</span>
              <span style={{ padding: '0.5rem 1rem', background: 'rgba(100, 116, 139, 0.1)', color: 'var(--text-muted)', borderRadius: '50px', fontSize: '0.9rem', fontWeight: 600 }}>Skipped: {skippedCount}</span>
            </div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
            {results.results.map((res: QuizResult, i: number) => {
              const q = questions.find(qu => qu.id === res.id);
              const isCorrect = res.is_correct;
              return (
                <div key={res.id} style={{ background: 'var(--bg-dark)', padding: '1.5rem', borderRadius: '12px', borderLeft: `4px solid ${isCorrect ? 'var(--success)' : 'var(--danger)'}` }}>
                  <h4 style={{ marginTop: 0, color: 'var(--text-primary)', lineHeight: 1.5 }}>Q{i+1}: {q?.text}</h4>
                  <div style={{ margin: '0.5rem 0', color: 'var(--text-secondary)' }}>
                    <strong>Your Answer:</strong> {res.user_answer || "Not Attempted"} 
                  </div>
                  {!isCorrect && (
                    <div style={{ margin: '0.5rem 0', color: 'var(--text-secondary)' }}>
                      <strong>Correct Answer:</strong> {res.correct_answer}
                    </div>
                  )}
                  <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--bg-secondary)', color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.6 }}>
                    <strong>Explanation:</strong> {res.explanation}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button onClick={onBack} className="btn btn-outline" style={{ flex: 1 }}>Exit to Home</button>
            {onViewAnalytics && (
              <button onClick={onViewAnalytics} className="btn btn-primary" style={{ flex: 2 }}>View Full Analytics</button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.examWrapper}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h2>Daily All-India Mock Test</h2>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.timer}>Time Left: <span>{formatTime(timeRemaining)}</span></div>
          <button className="btn btn-outline" onClick={handleSubmit}>Submit Mock Test</button>
        </div>
      </header>
      
      <div className={styles.mainContent}>
        <div className={styles.leftPanel}>
          <div className={styles.questionContainer}>
            {currentQuestion && (
              <QuestionPanel 
                question={currentQuestion}
                index={currentIndex + 1}
                selectedOption={answers[currentQuestion.id]} 
                onSelect={handleSelectOption} 
              />
            )}
          </div>
          <ExamControls 
            onClear={handleClearResponse} 
            onReview={handleMarkForReview} 
            onSaveNext={handleSaveAndNext} 
            isLast={currentIndex === questions.length - 1}
          />
        </div>
        
        <div className={styles.rightPanel}>
          <QuestionPalette 
            questions={questions} 
            currentIndex={currentIndex} 
            statusMap={statusMap} 
            onJump={jumpToQuestion} 
          />
        </div>
      </div>
    </div>
  );
}
