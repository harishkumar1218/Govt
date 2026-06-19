import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './PerformancePage.module.css';

interface Props {
  onBack: () => void;
  onViewDetail?: (submissionId: number) => void;
}

export default function PerformancePage({ onBack, onViewDetail }: Props) {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    try {
      setLoading(true);
      const [analyticsRes, historyRes] = await Promise.all([
        fetch(apiUrl('/api/user/analytics/'), {
          headers: { 'Authorization': `Token ${token}` }
        }),
        fetch(apiUrl('/api/user/mock-history/'), {
          headers: { 'Authorization': `Token ${token}` }
        })
      ]);

      if (analyticsRes.ok && historyRes.ok) {
        const analyticsData = await analyticsRes.json();
        const historyData = await historyRes.json();
        setAnalytics(analyticsData);
        setHistory(historyData);
      }
    } catch (err) {
      console.error("Failed to fetch performance data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = (submissionId: number) => {
    if (onViewDetail) {
      onViewDetail(submissionId);
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

  if (loading) {
    return (
      <div className={styles.wrapper}>
        <header className={styles.header}>
          <div className={`container ${styles.headerInner}`}>
            <button className="btn" onClick={onBack}>← Back to Home</button>
            <div className={styles.logo}>My Analytics</div>
            <div style={{ width: '100px' }}></div>
          </div>
        </header>
        <div style={{ textAlign: 'center', padding: '4rem' }}>Loading advanced analytics...</div>
      </div>
    );
  }

  if (!analytics) return null;

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          <button className="btn" onClick={onBack}>← Back to Home</button>
          <div className={styles.logo}>UPSC Aspire Analytics</div>
          <div style={{ width: '100px' }}></div>
        </div>
      </header>

      <main className="container">
        <div className={styles.dashboardHeader}>
          <h1 className={styles.title}>Your Performance Dashboard</h1>
          <p className={styles.subtitle}>Track your progress, identify weaknesses, and conquer the exams.</p>
        </div>

        {/* Top KPIs */}
        <div className={styles.kpiGrid}>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Total Tests</span>
            <span className={styles.kpiValue}>{analytics.total_tests}</span>
          </div>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Avg Score</span>
            <span className={styles.kpiValue}>{analytics.avg_score_percentage}%</span>
          </div>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Accuracy</span>
            <span className={styles.kpiValue}>{analytics.avg_accuracy}%</span>
          </div>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Readiness</span>
            <span className={styles.kpiValue}>{analytics.readiness_score}<span className={styles.kpiValSmall}>/100</span></span>
          </div>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Global Rank</span>
            <span className={styles.kpiValue}>#{analytics.rank}</span>
          </div>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Current Streak</span>
            <span className={styles.kpiValue}>{analytics.streak} 🔥</span>
          </div>
        </div>

        <div className={styles.chartsGrid}>
          {/* Trend Chart (Simple CSS implementation) */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>Recent Score Trend</h2>
            </div>
            {analytics.trend_scores && analytics.trend_scores.length > 0 ? (
              <div className={styles.chartContainer}>
                {analytics.trend_scores.slice(-10).map((score: number, idx: number) => {
                  const dateLabel = analytics.trend_dates.slice(-10)[idx];
                  return (
                    <div key={idx} className={styles.chartBarWrapper}>
                      <div className={styles.chartTooltip}>
                        {dateLabel}: {score}%
                      </div>
                      <div 
                        className={styles.chartBar} 
                        style={{ height: `${Math.max(score, 5)}%` }}
                      ></div>
                      <div className={styles.chartLabel}>T{idx + 1}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p>No enough data for trend chart.</p>
            )}
          </div>

          {/* Risk Profile */}
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>Risk Profile</h2>
            </div>
            <div className={styles.riskProfile}>
              {analytics.risk_profile === 'Balanced' && <div className={styles.riskBadge}>⚖️</div>}
              {analytics.risk_profile === 'Fast but Careless' && <div className={styles.riskBadge}>⚡</div>}
              {analytics.risk_profile === 'Slow but Accurate' && <div className={styles.riskBadge}>🐢</div>}
              {analytics.risk_profile === 'Too Many Guesses' && <div className={styles.riskBadge}>🎲</div>}
              
              <div className={styles.riskName}>{analytics.risk_profile}</div>
              <p className={styles.riskDesc}>
                {analytics.risk_profile === 'Balanced' && "You maintain a great balance between speed and accuracy. Keep it up!"}
                {analytics.risk_profile === 'Fast but Careless' && "You are fast, but negative marking is hurting you. Slow down and read carefully."}
                {analytics.risk_profile === 'Slow but Accurate' && "Your accuracy is great, but you need to improve your speed to finish the real exam."}
                {analytics.risk_profile === 'Too Many Guesses' && "You are attempting too many questions without certainty. Try skipping doubtful ones."}
              </p>
            </div>
          </div>
        </div>

        {/* History Table */}
        <div className={styles.historySection}>
          <div className={styles.historyHeader}>
            <h2 className={styles.cardTitle}>Mock Test History</h2>
          </div>
          
          {history.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No mock tests taken yet. Head back to the home page and start one!
            </div>
          ) : (
            <div className={styles.historyTableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Track & Topic</th>
                    <th>Score</th>
                    <th>Accuracy</th>
                    <th>Time</th>
                    <th>Rank</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((sub) => {
                    let scoreClass = styles.scoreAverage;
                    if (sub.percentage >= 80) scoreClass = styles.scoreExcellent;
                    else if (sub.percentage >= 60) scoreClass = styles.scoreGood;
                    else if (sub.percentage < 40) scoreClass = styles.scorePoor;

                    return (
                      <React.Fragment key={sub.submission_id}>
                        <tr className={styles.tableRow} onClick={() => handleRowClick(sub.submission_id)}>
                          <td>{new Date(sub.quiz_date).toLocaleDateString()}</td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{sub.track_title}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{sub.quiz_topic}</div>
                          </td>
                          <td>
                            <span className={`${styles.scoreBadge} ${scoreClass}`}>
                              {sub.score} / {sub.max_score} ({sub.percentage}%)
                            </span>
                          </td>
                          <td>{sub.accuracy}%</td>
                          <td>{formatTime(sub.time_taken_seconds)}</td>
                          <td>#{sub.rank}</td>
                        </tr>
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
