import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './ExamPage.module.css';
import QuestionPanel from '../components/exam/QuestionPanel';
import QuestionPalette from '../components/exam/QuestionPalette';
import ExamControls from '../components/exam/ExamControls';

interface Question {
  id: number;
  text: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

interface Props {
  onExit: () => void;
  trackSlug?: string;
  examSlug?: string;
}

export type QuestionStatus = 'unvisited' | 'answered' | 'unanswered' | 'marked';

export default function ExamPage({ onExit, trackSlug, examSlug }: Props) {
  const [mockQuestions, setMockQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [examTitle, setExamTitle] = useState('Mock Exam');
  
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [statusMap, setStatusMap] = useState<Record<number, QuestionStatus>>({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [examDuration, setExamDuration] = useState(0);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (trackSlug) params.set('track_slug', trackSlug);
    if (examSlug) params.set('exam_id', examSlug);

    fetch(apiUrl(`/api/generate-mock/?${params.toString()}`))
      .then(res => {
        if (!res.ok) throw new Error("Failed to generate exam questions. Is Ollama running?");
        return res.json();
      })
      .then(data => {
        if (data.questions && data.questions.length > 0) {
          setMockQuestions(data.questions);
          if (data.exam_name) setExamTitle(data.exam_name);
          if (data.duration_seconds) {
            setExamDuration(data.duration_seconds);
            setTimeLeft(data.duration_seconds);
          }
          
          const initialStatus: Record<number, QuestionStatus> = {};
          data.questions.forEach((q: Question) => {
            initialStatus[q.id] = 'unvisited';
          });
          initialStatus[data.questions[0].id] = 'unanswered';
          setStatusMap(initialStatus);
        } else {
          throw new Error("No questions returned from AI generation.");
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [trackSlug, examSlug]);

  useEffect(() => {
    if (!examDuration) return;
    const timer = setInterval(() => {
      setTimeLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [examDuration]);

  const currentQuestion = mockQuestions[currentIndex];

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
    if (currentIndex < mockQuestions.length - 1) {
      const nextId = mockQuestions[currentIndex + 1].id;
      setCurrentIndex(currentIndex + 1);
      setStatusMap(prev => ({
        ...prev,
        [nextId]: prev[nextId] === 'unvisited' ? 'unanswered' : prev[nextId]
      }));
    }
  };

  const jumpToQuestion = (index: number) => {
    // Current question gets marked as unanswered if it was just visited and no answer
    const hasAnswer = answers[currentQuestion.id] !== undefined;
    if (statusMap[currentQuestion.id] === 'unanswered' && !hasAnswer) {
      // already unanswered
    }
    
    setCurrentIndex(index);
    const targetId = mockQuestions[index].id;
    setStatusMap(prev => ({
      ...prev,
      [targetId]: prev[targetId] === 'unvisited' ? 'unanswered' : prev[targetId]
    }));
  };

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className={styles.examWrapper} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <div className="spinner" style={{ width: '50px', height: '50px', border: '5px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <h2 style={{ marginTop: '2rem' }}>Generating Dynamic Exam Questions...</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>This may take a minute or two using the local AI model.</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.examWrapper} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
        <h2>Error Generating Exam</h2>
        <p style={{ color: 'var(--danger)', marginTop: '1rem', maxWidth: '600px', textAlign: 'center' }}>{error}</p>
        <button className="btn btn-primary" onClick={onExit} style={{ marginTop: '2rem' }}>Go Back</button>
      </div>
    );
  }

  return (
    <div className={styles.examWrapper}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h2>{examTitle}</h2>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.timer}>Time Left: <span>{formatTime(timeLeft)}</span></div>
          <button className="btn btn-outline" onClick={onExit}>Submit Exam</button>
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
            isLast={currentIndex === mockQuestions.length - 1}
          />
        </div>
        
        <div className={styles.rightPanel}>
          <QuestionPalette 
            questions={mockQuestions} 
            currentIndex={currentIndex} 
            statusMap={statusMap} 
            onJump={jumpToQuestion} 
          />
        </div>
      </div>
    </div>
  );
}
