import { useState } from 'react';
import { apiUrl } from '../config/api';
import QRCode from 'react-qr-code';
import styles from './EssayPracticePage.module.css';
import EssayScoreCard from '../components/essay/EssayScoreCard';
import EssayRubricBreakdown from '../components/essay/EssayRubricBreakdown';

interface Props {
  trackSlug: string;
  roadmapItemId: string;
  onBack: () => void;
}

export default function EssayPracticePage({ trackSlug, roadmapItemId, onBack }: Props) {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [analyzing, setAnalyzing] = useState<number | null>(null);

  const analyzeQuestion = async (questionId: number) => {
    setAnalyzing(questionId);
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/essay/questions/${questionId}/analyze/`), {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`
        }
      });
      if (res.ok) {
        // Refresh session to get updated question data including AI review
        await refreshSession();
      } else {
        const err = await res.json();
        alert(`Analysis failed: ${err.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
      alert('Network error during analysis.');
    } finally {
      setAnalyzing(null);
    }
  };

  const getUploadUrl = (token: string) => {
    // Determine the host. If somehow forced to https locally, fallback to http
    let origin = window.location.origin;
    if (origin.includes('localhost') || origin.includes('127.0.0.1')) {
      origin = origin.replace('https://', 'http://');
    }
    return `${origin}/essay-upload/${token}`;
  };



  const startSession = async () => {
    setLoading(true);
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl('/api/essay/sessions/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`
        },
        body: JSON.stringify({
          track_slug: trackSlug,
          roadmap_item_id: roadmapItemId,
          title: 'UPSC Mains Essay Practice'
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setSession(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const refreshSession = async () => {
    if (!session) return;
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/essay/sessions/${session.id}/`), {
        headers: {
          'Authorization': `Token ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const submitSession = async () => {
    if (!session) return;
    setSubmitting(true);
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/essay/sessions/${session.id}/submit/`), {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`
        }
      });
      if (res.ok) {
        setSubmitted(true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className={styles.wrapper}>
        <div className={`container ${styles.successScreen}`}>
          <div className={styles.successIcon}>🎉</div>
          <h1 className={styles.successTitle}>Essays Submitted Successfully!</h1>
          <p className={styles.subtitle}>Your answer sheets have been securely uploaded and sent for evaluation.</p>
          <button className={styles.btnPrimary} onClick={onBack}>Back to Roadmap</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <div className={`container ${styles.headerInner}`}>
          <button className="btn" onClick={onBack}>← Back to Roadmap</button>
          <div className={styles.logo}>UPSC Mains Practice</div>
          <div style={{ width: '150px' }}></div>
        </div>
      </header>

      <main className="container">
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>Write Essay on Paper</h1>
          <p className={styles.subtitle}>
            Unlike MCQs, UPSC Mains requires handwritten answers. 
            Write your essay on physical paper, scan the QR code with your phone camera, and securely upload the photos to your session.
          </p>
        </div>

        {!session && !loading && (
          <div style={{ textAlign: 'center', padding: '3rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)' }}>
            <h2>Ready to start writing?</h2>
            <p style={{ marginBottom: '2rem', color: 'var(--text-muted)' }}>We will generate essay prompts for you based on past UPSC patterns.</p>
            <button className={styles.btnPrimary} onClick={startSession}>Start Practice Session</button>
          </div>
        )}

        {loading && <div style={{ textAlign: 'center' }}>Generating Prompts...</div>}

        {session && (
          <>
            <div className={styles.questionsList}>
              {session.questions.map((q: any) => {
                const uploadUrl = getUploadUrl(q.upload_token);
                return (
                  <div key={q.id} className={styles.questionCard}>
                    <div className={styles.qContent}>
                      <div className={styles.qHeader}>
                        <div className={styles.qOrder}>Question {q.order}</div>
                        <div className={styles.qMarks}>{q.max_marks} Marks</div>
                      </div>
                      <div className={styles.qPrompt}>{q.prompt_text}</div>
                      
                      {q.images && q.images.length > 0 && (
                        <div className={styles.uploadStatus}>
                          ✅ {q.images.length} page(s) uploaded
                        </div>
                      )}
                      
                      {q.images && q.images.length > 0 && (
                        <div className={styles.thumbnailsList}>
                          {q.images.map((img: any) => (
                            <img key={img.id} src={apiUrl(`${img.image}`)} className={styles.thumbnail} alt="Upload" />
                          ))}
                        </div>
                      )}
                      
                      {q.images && q.images.length > 0 && !q.ai_review && (
                        <div style={{ marginTop: '1.5rem' }}>
                          <button 
                            className={styles.btnSecondary} 
                            onClick={() => analyzeQuestion(q.id)}
                            disabled={analyzing === q.id}
                          >
                            {analyzing === q.id ? 'Analyzing... (OCR & AI)' : '✨ Analyze Answer'}
                          </button>
                        </div>
                      )}
                      
                      {q.ai_review && q.ai_review.status === 'completed' && (
                        <div style={{ marginTop: '2rem' }}>
                          <EssayScoreCard 
                            score={q.ai_review.total_score} 
                            maxScore={q.ai_review.max_score} 
                            percentage={q.ai_review.percentage} 
                            ratingBand={q.ai_review.rating_band} 
                          />
                          
                          {q.transcript && (
                            <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                              <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-main)' }}>Extracted Text (OCR)</h4>
                              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                                Quality: {q.transcript.extraction_quality}. OCR may contain imperfections.
                              </p>
                              <div style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '0.9rem', whiteSpace: 'pre-wrap' }}>
                                {q.transcript.combined_text}
                              </div>
                            </div>
                          )}

                          <EssayRubricBreakdown rubric={q.ai_review.review_json.rubric} />
                          
                          <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div style={{ background: '#f0fdf4', padding: '1.5rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                              <h4 style={{ color: '#166534', marginTop: 0 }}>Strengths</h4>
                              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                              </ul>
                            </div>
                            <div style={{ background: '#fef2f2', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fecaca' }}>
                              <h4 style={{ color: '#991b1b', marginTop: 0 }}>Weaknesses</h4>
                              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.weaknesses.map((w: string, i: number) => <li key={i}>{w}</li>)}
                              </ul>
                            </div>
                          </div>

                          {q.ai_review.review_json.missing_dimensions && q.ai_review.review_json.missing_dimensions.length > 0 && (
                            <div style={{ marginTop: '1rem', background: '#fffbeb', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fde68a' }}>
                              <h4 style={{ color: '#92400e', marginTop: 0 }}>Missing Dimensions / Perspectives</h4>
                              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.review_json.missing_dimensions.map((m: string, i: number) => <li key={i}>{m}</li>)}
                              </ul>
                            </div>
                          )}

                          {q.ai_review.review_json.factual_or_logic_issues && q.ai_review.review_json.factual_or_logic_issues.length > 0 && (
                            <div style={{ marginTop: '1rem', background: '#fdf2f8', padding: '1.5rem', borderRadius: '8px', border: '1px solid #fbcfe8' }}>
                              <h4 style={{ color: '#9d174d', marginTop: 0 }}>Factual or Logic Issues</h4>
                              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.review_json.factual_or_logic_issues.map((f: string, i: number) => <li key={i}>{f}</li>)}
                              </ul>
                            </div>
                          )}

                          {q.ai_review.review_json.structure_feedback && (
                            <div style={{ marginTop: '1rem', padding: '1.5rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                              <h4 style={{ color: 'var(--text-main)', marginTop: 0 }}>Structure Feedback</h4>
                              <div style={{ fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                <div><strong>Introduction:</strong> {q.ai_review.review_json.structure_feedback.intro}</div>
                                <div><strong>Body:</strong> {q.ai_review.review_json.structure_feedback.body}</div>
                                <div><strong>Conclusion:</strong> {q.ai_review.review_json.structure_feedback.conclusion}</div>
                              </div>
                            </div>
                          )}

                          {q.ai_review.review_json.suggested_outline && q.ai_review.review_json.suggested_outline.length > 0 && (
                            <div style={{ marginTop: '1rem', padding: '1.5rem', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                              <h4 style={{ color: '#1e40af', marginTop: 0 }}>Suggested Outline for an Ideal Answer</h4>
                              <ol style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.review_json.suggested_outline.map((o: string, i: number) => <li key={i}>{o}</li>)}
                              </ol>
                            </div>
                          )}

                          {q.ai_review.review_json.model_answer_direction && (
                            <div style={{ marginTop: '1rem', padding: '1.5rem', background: '#f5f3ff', borderRadius: '8px', border: '1px solid #ddd6fe' }}>
                              <h4 style={{ color: '#5b21b6', marginTop: 0 }}>Model Answer Direction</h4>
                              <p style={{ margin: 0, fontSize: '0.9rem' }}>{q.ai_review.review_json.model_answer_direction}</p>
                            </div>
                          )}

                          {q.ai_review.review_json.next_practice_tasks && q.ai_review.review_json.next_practice_tasks.length > 0 && (
                            <div style={{ marginTop: '1rem', padding: '1.5rem', background: '#f0fdfa', borderRadius: '8px', border: '1px solid #a7f3d0' }}>
                              <h4 style={{ color: '#0f766e', marginTop: 0 }}>Next Steps & Recommended Practice</h4>
                              <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.9rem' }}>
                                {q.ai_review.review_json.next_practice_tasks.map((n: string, i: number) => <li key={i}>{n}</li>)}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                    
                    <div className={styles.qrContainer}>
                      <div className={styles.qrLabel}>Scan to Upload Answer</div>
                      <QRCode value={uploadUrl} size={150} level="M" />
                      <div className={styles.qrHelp}>Open phone camera and scan</div>
                      <a 
                        href={uploadUrl} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className={styles.uploadLink}
                      >
                        Or upload from this device
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className={styles.actionsBar}>
              <button className={styles.btnSecondary} onClick={refreshSession}>
                🔄 Refresh Uploads
              </button>
              <button 
                className={styles.btnPrimary} 
                onClick={submitSession} 
                disabled={submitting}
              >
                {submitting ? 'Submitting...' : 'Submit for Evaluation'}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
