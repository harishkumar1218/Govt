import { useState, useEffect } from 'react';
import { apiUrl, fetchPlatformConfig, formatQuizStartTime, type PlatformConfig } from '../config/api';
import styles from './TrackDetailsPage.module.css';
import LearningRoadmap from '../components/roadmap/LearningRoadmap';

interface Props {
  trackId: string;
  onBack: () => void;
  onStartMock: (quizId: number) => void;
  onStartEssay?: (roadmapItemId: string) => void;
}

export default function TrackDetailsPage({ trackId, onBack, onStartMock, onStartEssay }: Props) {
  const [track, setTrack] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'roadmap' | 'architecture' | 'syllabus' | 'eligibility' | 'verification' | 'cutoffs'>('roadmap');
  const [selectedCategory, setSelectedCategory] = useState<string>('General');
  const [platformConfig, setPlatformConfig] = useState<PlatformConfig | null>(null);

  // Daily Mock Test States
  const [quiz, setQuiz] = useState<any>(null);
  const [quizLoading, setQuizLoading] = useState(true);
  const [countdown, setCountdown] = useState<string>('00:00:00');
  const [isRegisteredState, setIsRegisteredState] = useState(false);
  const [statusState, setStatusState] = useState<string>('');
  const [canStartState, setCanStartState] = useState(false);
  const [mobileTooltipOpen, setMobileTooltipOpen] = useState(false);

  const fetchTodayQuiz = async () => {
    const token = localStorage.getItem('auth_token');
    try {
      const headers: any = {};
      if (token) {
        headers['Authorization'] = `Token ${token}`;
      }
      const res = await fetch(apiUrl(`/api/quiz/today/?track=${trackId}`), { headers });
      if (res.status === 404) {
        setQuiz(null);
      } else if (res.ok) {
        const data = await res.json();
        setQuiz(data);
        setIsRegisteredState(data.is_registered);
        setStatusState(data.status);
        setCanStartState(data.can_start);
      } else {
        console.error("Failed to load quiz");
      }
    } catch (err) {
      console.error("Failed to load quiz", err);
    } finally {
      setQuizLoading(false);
    }
  };

  useEffect(() => {
    fetchPlatformConfig().then(setPlatformConfig).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    setQuizLoading(true);

    fetch(apiUrl(`/api/tracks/${trackId}/`))
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(data => {
        setTrack(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load track details", err);
        setLoading(false);
      });

    fetchTodayQuiz();
  }, [trackId]);

  // Handle registration click
  const handleRegister = async () => {
    if (!quiz) return;
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    try {
      const res = await fetch(apiUrl(`/api/quiz/${quiz.id}/register/`), {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        setIsRegisteredState(true);
        fetchTodayQuiz();
      } else {
        alert("Failed to register");
      }
    } catch (err) {
      console.error("Registration error", err);
    }
  };

  // Close mobile tooltip when clicking outside
  useEffect(() => {
    const handleOutsideClick = () => {
      setMobileTooltipOpen(false);
    };
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);

  // Countdown timer calculation
  useEffect(() => {
    if (!quiz) return;

    const calculateCountdown = () => {
      const now = new Date();
      let targetDate = new Date();

      if (quiz.starts_at) {
        targetDate = new Date(quiz.starts_at);
      } else {
        const hour = platformConfig?.quiz.default_start_hour ?? 18;
        const minute = platformConfig?.quiz.default_start_minute ?? 0;
        targetDate.setHours(hour, minute, 0, 0);
      }

      const diff = targetDate.getTime() - now.getTime();

      if (diff <= 0) {
        setCountdown('00:00:00');
        fetchTodayQuiz();
        return true;
      } else {
        const totalSeconds = Math.floor(diff / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        const pad = (num: number) => num.toString().padStart(2, '0');
        setCountdown(`${pad(hours)}:${pad(minutes)}:${pad(seconds)}`);
        return false;
      }
    };

    const shouldStop = calculateCountdown();
    if (shouldStop) return;

    const interval = setInterval(() => {
      const stop = calculateCountdown();
      if (stop) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [quiz, platformConfig]);

  const quizStartFallback = () => {
    const hour = platformConfig?.quiz.default_start_hour ?? 18;
    const minute = platformConfig?.quiz.default_start_minute ?? 0;
    const d = new Date();
    d.setHours(hour, minute, 0, 0);
    return d;
  };
  const quizStartLabel = formatQuizStartTime(quiz?.starts_at, platformConfig);
  const categories = platformConfig?.eligibility_categories ?? ['General', 'EWS', 'OBC', 'SC', 'ST'];

  if (loading) {
    return (
      <div className={styles.wrapper} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Loading live data from database...</p>
      </div>
    );
  }

  if (!track) {
    return (
      <div className={styles.wrapper}>
        <div className="container" style={{ padding: '4rem 0' }}>
          <h2>Track not found</h2>
          <button className="btn btn-primary" onClick={onBack} style={{ marginTop: '1rem' }}>Go Back</button>
        </div>
      </div>
    );
  }

  // Group cutoffs by sub_exam_name
  const groupedCutoffs: Record<string, any[]> = {};
  if (track.cutoffs) {
    track.cutoffs.forEach((cutoff: any) => {
      if (!groupedCutoffs[cutoff.sub_exam_name]) {
        groupedCutoffs[cutoff.sub_exam_name] = [];
      }
      groupedCutoffs[cutoff.sub_exam_name].push(cutoff);
    });
  }

  const categoryEligibility = track?.eligibility?.category_eligibility?.[selectedCategory] || {
    age_limit: track?.eligibility?.age_limit || 'Not specified',
    attempts: 'Not specified',
    relaxation_details: ''
  };

  const categoryVerification = track?.verification?.category_verification?.[selectedCategory] || {
    documents: track?.verification?.documents_required || []
  };

  const isCategorySpecificDoc = (docName: string) => {
    if (selectedCategory === 'General') return false;
    const generalDocs = track?.verification?.category_verification?.['General']?.documents || track?.verification?.documents_required || [];
    return !generalDocs.includes(docName);
  };

  return (
    <div className={styles.wrapper}>
      {/* Dynamic Header */}
      <header className={styles.header} style={{ background: track.gradient }}>
        <div className={`container ${styles.headerInner}`}>
          <div className={styles.headerLeft}>
            <button className={styles.backBtn} onClick={onBack}>
              <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"></line>
                <polyline points="12 19 5 12 12 5"></polyline>
              </svg>
              Back
            </button>
            <div className={styles.headerTitles}>
              <span className={styles.subtitle}>{track.subtitle}</span>
              <h1 className={styles.title}>{track.title}</h1>
            </div>
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <div className={`container ${styles.tabsContainer}`}>
          <div className={styles.tabs}>
            <button className={`${styles.tab} ${activeTab === 'roadmap' ? styles.activeTab : ''}`} onClick={() => setActiveTab('roadmap')}>Roadmap</button>
            <button className={`${styles.tab} ${activeTab === 'architecture' ? styles.activeTab : ''}`} onClick={() => setActiveTab('architecture')}>Architecture</button>
            <button className={`${styles.tab} ${activeTab === 'syllabus' ? styles.activeTab : ''}`} onClick={() => setActiveTab('syllabus')}>Syllabus</button>
            <button className={`${styles.tab} ${activeTab === 'eligibility' ? styles.activeTab : ''}`} onClick={() => setActiveTab('eligibility')}>Eligibility</button>
            <button className={`${styles.tab} ${activeTab === 'verification' ? styles.activeTab : ''}`} onClick={() => setActiveTab('verification')}>Verification</button>
            <button className={`${styles.tab} ${activeTab === 'cutoffs' ? styles.activeTab : ''}`} onClick={() => setActiveTab('cutoffs')}>Cut-offs</button>
          </div>
        </div>
      </header>

      <main className={`container ${styles.content}`}>
        {/* Roadmap Tab */}
        {activeTab === 'roadmap' && (
          <>
            {/* Daily Mock Test Banner */}
            {quizLoading ? (
              <div className={styles.mockLoading}>Loading today's Mock Test details...</div>
            ) : quiz ? (
              <div className={styles.mockTestSection}>
                <div className={styles.mockTestHeader}>
                  <div className={styles.mockHeaderLeft}>
                    <div className={styles.mockBadge}>Daily All-India Mock Test</div>
                    <h2 className={styles.mockTitle}>
                      {quiz.topic}
                      <div className={styles.infoWrapper}>
                        <button 
                          type="button"
                          className={styles.infoBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            setMobileTooltipOpen(!mobileTooltipOpen);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setMobileTooltipOpen(!mobileTooltipOpen);
                            }
                          }}
                          aria-label="Daily Mock Test Information"
                        >
                          i
                        </button>
                        <div 
                          className={`${styles.tooltip} ${mobileTooltipOpen ? styles.tooltipVisible : ''}`}
                          role="tooltip"
                        >
                          This Daily Mock Test is conducted All India wide at the same time for all registered aspirants.
                        </div>
                      </div>
                    </h2>
                    <div className={styles.mockMeta}>
                      <span className={styles.metaItem}><strong>Track:</strong> {quiz.track}</span>
                      <span className={styles.metaItem}><strong>Stage:</strong> {quiz.stage_name}</span>
                      <span className={styles.metaItem}><strong>Duration:</strong> {Math.round(quiz.duration_seconds / 60)} Mins</span>
                      <span className={styles.metaItem}><strong>Marks:</strong> {quiz.total_marks} Marks</span>
                    </div>
                  </div>
                  <div className={styles.mockHeaderRight}>
                    {statusState === 'Closed' ? (
                      <div className={styles.mockStatusClosed}>Exam Closed</div>
                    ) : (
                      <>
                        <div className={styles.timerWrapper}>
                          <span className={styles.timerLabel}>
                            {new Date() < (quiz.starts_at ? new Date(quiz.starts_at) : quizStartFallback()) 
                              ? 'Starts In' 
                              : 'Time Remaining'}
                          </span>
                          <span className={styles.timerValue}>{countdown}</span>
                        </div>
                        
                        <div className={styles.actionArea}>
                          {!isRegisteredState && (
                            <button className={styles.registerBtn} onClick={handleRegister}>
                              Register for Mock Test
                            </button>
                          )}
                          {isRegisteredState && !canStartState && (
                            <button className={styles.registeredBtn} disabled>
                              Registered (Starts at {quizStartLabel})
                            </button>
                          )}
                          {isRegisteredState && canStartState && (
                            <button className={styles.startBtn} onClick={() => onStartMock(quiz.id)}>
                              Start Mock Test
                              <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="5 3 19 12 5 21 5 3"></polygon>
                              </svg>
                            </button>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className={styles.emptyMockState}>
                <div className={styles.emptyMockIcon}>
                  <svg viewBox="0 0 24 24" width="32" height="32" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <div className={styles.emptyMockContent}>
                  <h3>No Daily Mock Scheduled</h3>
                  <p>No daily mock scheduled for this path today.</p>
                </div>
              </div>
            )}
            <section className={styles.section} style={{ padding: 0 }}>
              <LearningRoadmap trackId={trackId} onStartEssay={onStartEssay} />
            </section>
          </>
        )}

        {/* Architecture Tab */}
        {activeTab === 'architecture' && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Exam Architecture</h2>
            <div className={styles.timeline}>
              {track.flowchart && track.flowchart.map((stage: any, index: number) => (
                <div key={index} className={styles.timelineItem}>
                  <div className={styles.timelineDot}>
                    {index + 1}
                  </div>
                  <div className={styles.timelineContent}>
                    <h3>{stage.title}</h3>
                    <div className={styles.stageMeta}>
                      <span className={styles.badge}>{stage.type}</span>
                      <span className={styles.duration}>
                        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        {stage.duration}
                      </span>
                    </div>
                    <p>{stage.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Syllabus Tab */}
        {activeTab === 'syllabus' && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Syllabus Overview</h2>
            <div className={styles.syllabusGrid}>
              {track.syllabus && track.syllabus.map((section: any, index: number) => {
                const percent = section.total_marks ? Math.round((section.highest_marks / section.total_marks) * 100) : 0;
                return (
                  <div key={index} className={styles.syllabusCard}>
                    <div className={styles.syllabusCardHeader}>
                      <h3>{section.topic}</h3>
                      {section.total_marks > 0 && (
                        <span className={styles.totalMarksBadge}>
                          {section.total_marks} Marks
                        </span>
                      )}
                    </div>
                    
                    {section.total_marks > 0 && (
                      <div className={styles.marksProgressContainer}>
                        <div className={styles.marksProgressText}>
                          <span>Highest Score in History: <strong>{section.highest_marks}</strong> / {section.total_marks}</span>
                          <span className={styles.marksProgressPercent}>{percent}%</span>
                        </div>
                        <div className={styles.marksProgressBarTrack}>
                          <div 
                            className={styles.marksProgressBarFill} 
                            style={{ 
                              width: `${percent}%`, 
                              background: track.gradient || 'linear-gradient(90deg, var(--primary) 0%, #a855f7 100%)' 
                            }}
                          ></div>
                        </div>
                        {section.highest_marks_info && (
                          <div className={styles.marksTopperInfo}>
                            <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className={styles.starIcon}>
                              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
                            </svg>
                            <span>Record: {section.highest_marks_info}</span>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className={styles.divider}></div>
                    
                    <ul className={styles.listStyle}>
                      {section.details.map((item: string, i: number) => (
                        <li key={i}>
                          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className={styles.checkIcon}>
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Eligibility Tab */}
        {activeTab === 'eligibility' && track.eligibility && (
          <section className={styles.section}>
            <div className={styles.sectionHeaderFlex}>
              <h2 className={styles.sectionTitle}>Eligibility Criteria</h2>
              
              {/* Category Selector */}
              <div className={styles.categorySelector}>
                <span className={styles.categoryLabel}>Category:</span>
                <div className={styles.categoryPills}>
                  {categories.map(cat => (
                    <button
                      key={cat}
                      className={`${styles.categoryPill} ${selectedCategory === cat ? styles.activeCategoryPill : ''} ${styles['pill' + cat]}`}
                      onClick={() => setSelectedCategory(cat)}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className={styles.eligibilityGrid}>
              <div className={styles.eligibilityCard}>
                <div className={styles.eligibilityIcon}>
                  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                </div>
                <div>
                  <h3>Age Limit ({selectedCategory})</h3>
                  <p>{categoryEligibility.age_limit}</p>
                </div>
              </div>
              <div className={styles.eligibilityCard}>
                <div className={styles.eligibilityIcon}>
                  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                </div>
                <div>
                  <h3>Number of Attempts</h3>
                  <p>{categoryEligibility.attempts}</p>
                </div>
              </div>
              <div className={styles.eligibilityCard}>
                <div className={styles.eligibilityIcon}>
                  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>
                </div>
                <div>
                  <h3>Educational Qualification</h3>
                  <p>{track.eligibility.educational_qualification}</p>
                </div>
              </div>
              <div className={styles.eligibilityCard}>
                <div className={styles.eligibilityIcon}>
                  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                </div>
                <div>
                  <h3>Nationality</h3>
                  <p>{track.eligibility.nationality}</p>
                </div>
              </div>
            </div>

            {categoryEligibility.relaxation_details && (
              <div className={styles.eligibilityNotes} style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--primary)' }}>
                <h4>Category-Specific Relaxations ({selectedCategory})</h4>
                <p style={{ color: 'var(--text-muted)', lineHeight: '1.6', fontSize: '1.05rem', margin: 0 }}>
                  {categoryEligibility.relaxation_details}
                </p>
              </div>
            )}
            
            {track.eligibility.other_details && Object.keys(track.eligibility.other_details).length > 0 && (
              <div className={styles.eligibilityNotes}>
                <h4>Additional Requirements</h4>
                <ul className={styles.listStyle}>
                  {Object.entries(track.eligibility.other_details).map(([key, value], i) => (
                    <li key={i}>
                      <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className={styles.infoIcon}>
                        <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>
                      </svg>
                      <strong>{key}:</strong> {value as string}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* Verification Tab */}
        {activeTab === 'verification' && track.verification && (
          <section className={styles.section}>
            <div className={styles.sectionHeaderFlex}>
              <h2 className={styles.sectionTitle}>Document Verification</h2>
              
              {/* Category Selector */}
              <div className={styles.categorySelector}>
                <span className={styles.categoryLabel}>Category:</span>
                <div className={styles.categoryPills}>
                  {categories.map(cat => (
                    <button
                      key={cat}
                      className={`${styles.categoryPill} ${selectedCategory === cat ? styles.activeCategoryPill : ''} ${styles['pill' + cat]}`}
                      onClick={() => setSelectedCategory(cat)}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className={styles.verificationContainer}>
              <div className={styles.verificationIntro}>
                <p>{track.verification.process_description}</p>
              </div>
              
              <div className={styles.checklistCard}>
                <h3>Required Document Checklist ({selectedCategory})</h3>
                <ul className={styles.checklist}>
                  {categoryVerification.documents.map((doc: string, i: number) => {
                    const isSpecific = isCategorySpecificDoc(doc);
                    return (
                      <li key={i} className={`${styles.checklistItem} ${isSpecific ? styles.specificItem : ''}`}>
                        <label className={styles.checkboxContainer}>
                          <input type="checkbox" />
                          <span className={styles.checkmark}></span>
                          <span className={styles.docName}>
                            {doc}
                            {isSpecific && (
                              <span className={`${styles.categoryBadge} ${styles['badge' + selectedCategory]}`}>
                                {selectedCategory} Required
                              </span>
                            )}
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </section>
        )}

        {/* Cut-offs Tab */}
        {activeTab === 'cutoffs' && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Historical Cut-offs</h2>
            {Object.keys(groupedCutoffs).length === 0 ? (
              <p className={styles.noDataMsg}>Cut-off data is not available yet.</p>
            ) : (
              <div className={styles.cutoffsContainer}>
                {Object.entries(groupedCutoffs).map(([subExam, records]) => {
                  // Get all unique stages from the JSON for this sub_exam to build table headers
                  const allStages = new Set<string>();
                  records.forEach(r => Object.keys(r.stages).forEach(s => allStages.add(s)));
                  const stageColumns = Array.from(allStages);

                  return (
                    <div key={subExam} className={styles.cutoffTableCard}>
                      <h3>{subExam}</h3>
                      <div className={styles.tableWrapper}>
                        <table className={styles.cutoffTable}>
                          <thead>
                            <tr>
                              <th>Year</th>
                              <th>Category</th>
                              {stageColumns.map(stage => (
                                <th key={stage}>{stage}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {records.map((record, i) => (
                              <tr key={i}>
                                <td className={styles.tdYear}>{record.year}</td>
                                <td>{record.category}</td>
                                {stageColumns.map(stage => (
                                  <td key={stage}>{record.stages[stage] || '-'}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

      </main>
    </div>
  );
}
