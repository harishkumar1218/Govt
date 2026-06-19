/* eslint-disable @typescript-eslint/no-unused-vars */
import { apiUrl } from './config/api';
import { useState, useEffect } from 'react';
import LandingPage from './pages/LandingPage';
import ExamPage from './pages/ExamPage';
import LoginPage from './pages/LoginPage';
import TrackDetailsPage from './pages/TrackDetailsPage';
import CurrentAffairsPage from './pages/CurrentAffairsPage';
import DailyQuizPage from './pages/DailyQuizPage';

import PerformancePage from './pages/PerformancePage';

import PerformanceDetailPage from './pages/PerformanceDetailPage';

import EssayPracticePage from './pages/EssayPracticePage';
import EssayMobileUploadPage from './pages/EssayMobileUploadPage';
import StaffEssayReviewPage from './pages/StaffEssayReviewPage';

export type AppState = 'loading' | 'login' | 'landing' | 'trackDetails' | 'exam' | 'current-affairs' | 'dailyQuiz' | 'performance' | 'performanceDetail' | 'essayPractice';

function App() {
  const [appState, setAppState] = useState<AppState>('loading');
  const [_user, setUser] = useState<any>(null);
  const [selectedTrack, setSelectedTrack] = useState<string>('upsc');
  const [selectedQuizId, setSelectedQuizId] = useState<number | null>(null);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | null>(null);
  const [selectedRoadmapItem, setSelectedRoadmapItem] = useState<string | null>(null);

  // Handle direct QR code link routing
  const path = window.location.pathname;
  if (path.startsWith('/essay-upload/')) {
    const token = path.split('/')[2];
    return <EssayMobileUploadPage token={token} />;
  }
  
  if (path.startsWith('/staff/essay-review/')) {
    const sessionId = parseInt(path.split('/')[3], 10);
    return <StaffEssayReviewPage sessionId={sessionId} />;
  }

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setAppState('login');
      return;
    }

    // Verify token with Django backend
    fetch(apiUrl('/auth/user/'), {
      headers: {
        'Authorization': `Token ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('Token invalid');
        return res.json();
      })
      .then(data => {
        setUser(data);
        setAppState('landing');
      })
      .catch(err => {
        console.error("Auth check failed", err);
        localStorage.removeItem('auth_token');
        setAppState('login');
      });
  }, []);

  const handleLoginSuccess = (token: string) => {
    localStorage.setItem('auth_token', token);
    setAppState('landing');
  };



  if (appState === 'loading') {
    return <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh'}}>Loading...</div>;
  }

  return (
    <div className="app-container">
      {appState === 'login' && <LoginPage onLoginSuccess={handleLoginSuccess} />}
      {appState === 'landing' && (
        <LandingPage 
          onSelectTrack={(trackId) => {
            setSelectedTrack(trackId);
            setAppState('trackDetails');
          }}
          onNavigateCurrentAffairs={() => setAppState('current-affairs')}
          onNavigatePerformance={() => setAppState('performance')}
        />
      )}
      {appState === 'trackDetails' && (
        <TrackDetailsPage 
          trackId={selectedTrack} 
          onBack={() => setAppState('landing')} 
          onStartMock={(quizId) => {
            setSelectedQuizId(quizId);
            setAppState('dailyQuiz');
          }} 
          onStartEssay={(roadmapItemId) => {
            setSelectedRoadmapItem(roadmapItemId);
            setAppState('essayPractice');
          }}
        />
      )}
      {appState === 'exam' && (
        <ExamPage trackSlug={selectedTrack} onExit={() => setAppState('landing')} />
      )}
      {appState === 'current-affairs' && <CurrentAffairsPage onBack={() => setAppState('landing')} />}
      {appState === 'dailyQuiz' && selectedQuizId && (
        <DailyQuizPage quizId={selectedQuizId} onBack={() => setAppState('landing')} onViewAnalytics={() => setAppState('performance')} />
      )}
      {appState === 'performance' && (
        <PerformancePage 
          onBack={() => setAppState('landing')} 
          onViewDetail={(subId) => {
            setSelectedSubmissionId(subId);
            setAppState('performanceDetail');
          }}
        />
      )}
      {appState === 'performanceDetail' && selectedSubmissionId && (
        <PerformanceDetailPage 
          submissionId={selectedSubmissionId} 
          onBack={() => setAppState('performance')} 
        />
      )}
      {appState === 'essayPractice' && selectedRoadmapItem && (
        <EssayPracticePage 
          trackSlug={selectedTrack}
          roadmapItemId={selectedRoadmapItem}
          onBack={() => setAppState('trackDetails')}
        />
      )}
    </div>
  );
}

export default App;
