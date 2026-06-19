import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';

interface Props {
  sessionId: number;
}

export default function StaffEssayReviewPage({ sessionId }: Props) {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [overrideScore, setOverrideScore] = useState<number | ''>('');
  const [overrideFeedback, setOverrideFeedback] = useState('');

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  const fetchSession = async () => {
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/essay/reviewer/sessions/${sessionId}/`), {
        headers: {
          'Authorization': `Token ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        if (data.review) {
          setOverrideScore(data.review.marks_awarded);
          setOverrideFeedback(data.review.feedback);
        } else if (data.questions && data.questions[0]?.ai_review) {
           setOverrideScore(data.questions[0].ai_review.total_score);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const submitOverride = async () => {
    if (overrideScore === '') return;
    setSaving(true);
    const token = localStorage.getItem('auth_token');
    try {
      const res = await fetch(apiUrl(`/api/essay/reviewer/sessions/${sessionId}/override/`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`
        },
        body: JSON.stringify({
          marks_awarded: overrideScore,
          feedback: overrideFeedback,
        })
      });
      if (res.ok) {
        alert("Final review submitted successfully!");
        fetchSession();
      } else {
         const err = await res.json();
         alert("Failed to submit: " + JSON.stringify(err));
      }
    } catch (err) {
      console.error(err);
      alert("Network error.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading Session...</div>;
  if (!session) return <div style={{ padding: '2rem', textAlign: 'center' }}>Session not found.</div>;

  return (
    <div style={{ background: '#f8fafc', minHeight: '100vh', padding: '2rem 0' }}>
      <div className="container" style={{ maxWidth: '1000px', margin: '0 auto', background: '#fff', padding: '2rem', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
        <h1 style={{ marginTop: 0 }}>Staff Review Panel</h1>
        <div style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
          Session: {session.title} (ID: {session.id}) | Status: {session.status}
        </div>

        {session.questions.map((q: any) => (
          <div key={q.id} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1.5rem', marginBottom: '2rem' }}>
            <h3>Question {q.order} ({q.max_marks} Marks)</h3>
            <p style={{ fontStyle: 'italic', background: '#f1f5f9', padding: '1rem', borderRadius: '4px' }}>{q.prompt_text}</p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '1.5rem' }}>
              <div>
                <h4>Extracted Text (OCR)</h4>
                <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px', maxHeight: '400px', overflowY: 'auto', fontSize: '0.9rem', whiteSpace: 'pre-wrap', border: '1px solid #e2e8f0' }}>
                  {q.transcript ? q.transcript.combined_text : 'No transcript available.'}
                </div>
                
                {q.images && q.images.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h4>Original Uploads</h4>
                    <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto' }}>
                      {q.images.map((img: any) => (
                        <a href={apiUrl(`${img.image}`)} target="_blank" rel="noreferrer" key={img.id}>
                          <img src={apiUrl(`${img.image}`)} alt="page" style={{ height: '100px', borderRadius: '4px', border: '1px solid #ccc' }} />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div>
                <h4>AI Evaluation</h4>
                {q.ai_review ? (
                  <div style={{ background: '#f0fdf4', padding: '1rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#166534', marginBottom: '1rem' }}>
                      Suggested Score: {q.ai_review.total_score} / {q.ai_review.max_score}
                    </div>
                    {q.ai_review.review_json && (
                       <p style={{ fontSize: '0.9rem', margin: '0 0 1rem 0' }}>{q.ai_review.review_json.summary}</p>
                    )}
                    <h5 style={{ margin: '0 0 0.5rem 0' }}>Strengths:</h5>
                    <ul style={{ fontSize: '0.85rem', paddingLeft: '1.2rem', margin: '0 0 1rem 0' }}>
                      {q.ai_review.strengths?.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                    <h5 style={{ margin: '0 0 0.5rem 0' }}>Weaknesses:</h5>
                    <ul style={{ fontSize: '0.85rem', paddingLeft: '1.2rem', margin: '0 0 1rem 0' }}>
                      {q.ai_review.weaknesses?.map((w: string, i: number) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>No AI review generated yet.</div>
                )}
              </div>
            </div>
          </div>
        ))}

        <div style={{ background: '#fffbeb', padding: '2rem', borderRadius: '8px', border: '1px solid #fde68a' }}>
          <h2 style={{ marginTop: 0, color: '#92400e' }}>Final Assessor Override</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div>
              <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Final Score Override</label>
              <input 
                type="number" 
                value={overrideScore} 
                onChange={(e) => setOverrideScore(e.target.value === '' ? '' : Number(e.target.value))}
                style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid #ccc', width: '150px', fontSize: '1.1rem' }}
                placeholder="e.g. 110"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Final Feedback to Student</label>
              <textarea 
                value={overrideFeedback}
                onChange={(e) => setOverrideFeedback(e.target.value)}
                rows={5}
                style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #ccc', fontFamily: 'inherit' }}
                placeholder="Write your final evaluation feedback here..."
              />
            </div>
            <button 
              onClick={submitOverride}
              disabled={saving}
              style={{ background: '#b45309', color: 'white', padding: '1rem', border: 'none', borderRadius: '6px', fontSize: '1.1rem', cursor: 'pointer', fontWeight: 'bold' }}
            >
              {saving ? 'Saving...' : 'Submit Final Review'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
