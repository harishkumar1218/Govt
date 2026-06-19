import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './LandingPage.module.css';

interface Props {
  onSelectTrack: (trackId: string) => void;
  onNavigateCurrentAffairs: () => void;
  onNavigatePerformance: () => void;
}

export default function LandingPage({ onSelectTrack, onNavigateCurrentAffairs, onNavigatePerformance }: Props) {
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [leaderboardTracks, setLeaderboardTracks] = useState<any[]>([]);
  const [selectedTrackTab, setSelectedTrackTab] = useState<string>('');

  useEffect(() => {
    fetch(apiUrl('/api/tracks/'))
      .then(res => {
        if (!res.ok) throw new Error('Response not OK');
        return res.json();
      })
      .then(data => {
        if (Array.isArray(data)) {
          setExams(data);
        } else {
          throw new Error('Data is not an array');
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load tracks", err);
        setLoading(false);
      });

    fetch(apiUrl('/api/leaderboard/daily-latest/'))
      .then(res => res.json())
      .then(data => {
        if (data && data.tracks) {
          setLeaderboardTracks(data.tracks);
          if (data.tracks.length > 0) {
            setSelectedTrackTab(data.tracks[0].track_slug);
          }
        }
      })
      .catch(err => console.error("Failed to load daily leaderboard", err));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    window.location.reload();
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
  };


  const activeTrackData = leaderboardTracks.find(t => t.track_slug === selectedTrackTab);

  return (
    <div className={styles.wrapper}>
      <header className={`glass-header ${styles.header}`}>
        <div className={`container ${styles.headerInner}`}>
          <div className={styles.logo}>UPSC Aspire</div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button className="btn btn-secondary" onClick={onNavigatePerformance} id="btn-analytics">My Analytics</button>
            <button className="btn btn-primary" onClick={onNavigateCurrentAffairs} id="btn-daily-intel">Daily Intel (News)</button>
            <button className={styles.logoutBtn} onClick={handleLogout} id="btn-logout">Log Out</button>
          </div>
        </div>
      </header>
      
      <main className="container">
        <section className={styles.hero}>
          <h1 className={styles.title}>Supercharge Your Preparation with AI</h1>
          <p className={styles.subtitle}>
            Choose your examination track below. Our AI-powered mock tests and daily challenges are designed to boost active recall and accelerate your success.
          </p>
        </section>


        <section className={styles.tracksSection}>
          <div className={styles.tracksHeader}>
            <h2>Select Your Path</h2>
            <p>Swipe to explore available examination modules.</p>
          </div>
          
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>Loading live tracks from database...</div>
          ) : (
            <div className={styles.cardScrollContainer}>
              {exams.map((exam) => (
                <div 
                  key={exam.id} 
                  className={styles.examCard} 
                  style={{ background: exam.gradient }}
                >
                  <div className={styles.cardContent}>
                    <div className={styles.cardTop}>
                      <span className={styles.cardSubtitle}>{exam.subtitle}</span>
                      <h3 className={styles.cardTitle}>{exam.title}</h3>
                      <p className={styles.cardDesc}>{exam.description}</p>
                    </div>
                    <button className={styles.cardBtn} onClick={() => onSelectTrack(exam.id)}>
                      View Details
                      <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className={styles.btnIcon}>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                      </svg>
                    </button>
                  </div>
                  {/* Decorative background shapes for premium feel */}
                  <div className={styles.decorCircle1}></div>
                  <div className={styles.decorCircle2}></div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Daily Latest Leaderboard Section */}
        <section className={styles.leaderboardSection}>
          {/* Section header */}
          <div className={styles.leaderboardHeader}>
            <div className={styles.leaderboardBadge}>🏅 Live Rankings</div>
            <h2>Latest Daily Mock Rankers</h2>
            <p>Top 3 aspirants from the most recently completed daily mock test for each learning path.</p>
          </div>

          {/* Track selector tabs */}
          {leaderboardTracks.length > 0 && (
            <div className={styles.leaderboardTabsWrapper}>
              <div className={styles.leaderboardTabs}>
                {leaderboardTracks.map((track) => (
                  <button
                    key={track.track_slug}
                    className={`${styles.leaderboardTab} ${selectedTrackTab === track.track_slug ? styles.activeLeaderboardTab : ''}`}
                    onClick={() => setSelectedTrackTab(track.track_slug)}
                  >
                    {track.track_title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Panel */}
          {activeTrackData ? (
            <div className={styles.leaderboardPanel}>

              {activeTrackData.quiz_id ? (
                <>
                  {/* Quiz info banner */}
                  <div className={styles.quizInfoBanner}>
                    <div className={styles.quizInfoLeft}>
                      <span className={styles.quizInfoChip}>📝 Mock Test</span>
                      <span className={styles.quizTopic}>{activeTrackData.quiz_topic}</span>
                    </div>
                    <div className={styles.quizInfoRight}>
                      <span className={styles.quizDate}>{activeTrackData.quiz_date}</span>
                    </div>
                  </div>

                  {activeTrackData.rankers && activeTrackData.rankers.length > 0 ? (
                    <div className={styles.rankersGrid}>
                      {activeTrackData.rankers.map((ranker: any) => {
                        const initials = ranker.name
                          ? ranker.name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
                          : ranker.username.slice(0, 2).toUpperCase();
                        const rankColors = ['rank1', 'rank2', 'rank3'] as const;
                        const medals = ['🥇', '🥈', '🥉'];
                        return (
                          <div key={ranker.rank} className={`${styles.rankerCard} ${styles[rankColors[ranker.rank - 1]]}`}>
                            {/* Rank badge */}
                            <div className={styles.rankBadge}>
                              <span className={styles.rankMedal}>{medals[ranker.rank - 1]}</span>
                              <span className={styles.rankNumber}>#{ranker.rank}</span>
                            </div>

                            {/* Avatar */}
                            <div className={`${styles.rankerAvatar} ${styles['avatar' + ranker.rank]}`}>
                              {initials}
                            </div>

                            {/* Name & username */}
                            <div className={styles.rankerInfo}>
                              <h3 className={styles.rankerName}>{ranker.name}</h3>
                              <p className={styles.rankerUsername}>@{ranker.username}</p>
                            </div>

                            {/* Stats */}
                            <div className={styles.rankerStats}>
                              <div className={styles.statPill}>
                                <span className={styles.statPillLabel}>Score</span>
                                <span className={styles.statPillVal}>{typeof ranker.score === 'number' ? ranker.score.toFixed(1) : ranker.score}</span>
                              </div>
                              <div className={styles.statPill}>
                                <span className={styles.statPillLabel}>Accuracy</span>
                                <span className={styles.statPillVal}>{ranker.accuracy}%</span>
                              </div>
                              <div className={styles.statPill}>
                                <span className={styles.statPillLabel}>Time</span>
                                <span className={styles.statPillVal}>{formatTime(ranker.time_taken_seconds)}</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className={styles.emptySubmissions}>
                      <div className={styles.emptyIcon}>🎯</div>
                      <h3>No submissions yet</h3>
                      <p>Be the first to take today's mock test and claim the top spot!</p>
                    </div>
                  )}
                </>
              ) : (
                <div className={styles.emptySubmissions}>
                  <div className={styles.emptyIcon}>📅</div>
                  <h3>No mock scheduled</h3>
                  <p>No daily mock exam is scheduled yet for this learning path.</p>
                </div>
              )}
            </div>
          ) : (
            <div className={styles.leaderboardLoading}>
              <div className={styles.loadingDots}><span/><span/><span/></div>
              <p>Loading rankings...</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
