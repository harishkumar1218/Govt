import { useState, useEffect } from 'react';
import { apiUrl } from '../../config/api';
import styles from './LearningRoadmap.module.css';
import RoadmapNode from './RoadmapNode';

interface Props {
  trackId: string;
  onStartEssay?: (roadmapItemId: string) => void;
}

export default function LearningRoadmap({ trackId, onStartEssay }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem('auth_token');
    fetch(apiUrl(`/api/roadmap/${trackId}/`), {
      headers: {
        'Authorization': token ? `Token ${token}` : ''
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load roadmap data.');
        return res.json();
      })
      .then(resData => {
        setData(resData);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, [trackId]);

  const essayNodeIds = data?.phases
    ? new Set(
        data.phases.flatMap((phase: any) =>
          phase.nodes.filter((n: any) => n.tags?.includes('Essay')).map((n: any) => n.id)
        )
      )
    : new Set<string>();

  const handleComplete = (nodeId: string) => {
    if (essayNodeIds.has(nodeId) && onStartEssay) {
      onStartEssay(nodeId);
      return;
    }

    const token = localStorage.getItem('auth_token');
    fetch(apiUrl(`/api/roadmap/${trackId}/${nodeId}/complete/`), {
      method: 'POST',
      headers: {
        'Authorization': token ? `Token ${token}` : '',
        'Content-Type': 'application/json'
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to mark item as completed.');
        return res.json();
      })
      .then(resData => {
        if (resData.roadmap) {
          setData(resData.roadmap);
        }
      })
      .catch(err => {
        alert(err.message);
      });
  };

  if (loading) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading personalized roadmap...</div>;
  }

  if (error || !data) {
    return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>Failed to load roadmap: {error}</div>;
  }

  // Find the next recommended topic (using backend recommendation field)
  let nextTopic: any = null;
  if (data.recommended_next_item_id) {
    for (const phase of data.phases) {
      const found = phase.nodes.find((n: any) => n.id === data.recommended_next_item_id);
      if (found) {
        nextTopic = found;
        break;
      }
    }
  }

  return (
    <div className={styles.roadmapContainer}>
      {/* Main Tree Canvas */}
      <div className={styles.treeWrapper}>
        {data.phases.map((phase: any, pIndex: number) => (
          <div key={phase.id} className={styles.phaseContainer}>
            <div className={styles.phaseHeader}>
              <h2 className={styles.phaseTitle}>{pIndex + 1}. {phase.title}</h2>
            </div>
            
            <div className={styles.nodesGrid}>
              {phase.nodes.map((node: any, nIndex: number) => (
                <RoadmapNode 
                  key={node.id} 
                  node={node} 
                  isLast={nIndex === phase.nodes.length - 1} 
                  isRecommended={node.id === data.recommended_next_item_id}
                  onComplete={handleComplete}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Sticky Progress Sidebar */}
      <div className={styles.sidebar}>
        
        {/* Recommended Next Topic Card */}
        {nextTopic && (
          <div className={`${styles.sidebarCard} ${styles.nextTopicCard}`}>
            <h3 className={styles.sidebarTitle}>
              <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>
              </svg>
              Recommended Next
            </h3>
            <p style={{ fontWeight: 'bold', margin: '0.5rem 0' }}>{nextTopic.title}</p>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{nextTopic.description}</p>
            
            {data.priority_reason && (
              <p style={{ fontSize: '0.85rem', color: 'var(--primary)', marginTop: '0.5rem', fontStyle: 'italic', borderLeft: '2px solid var(--primary)', paddingLeft: '8px', lineHeight: '1.4' }}>
                💡 {data.priority_reason}
              </p>
            )}
            
            <button 
              className="btn btn-primary" 
              style={{ width: '100%', marginTop: '1rem', padding: '0.5rem' }}
              onClick={() => handleComplete(nextTopic.id)}
            >
              Mark Completed
            </button>
          </div>
        )}

        {/* Progress Stats Card */}
        <div className={styles.sidebarCard}>
          <h3 className={styles.sidebarTitle}>
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
            </svg>
            My Progress
          </h3>
          
          <div className={styles.progressWrapper}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className={styles.statLabel}>Overall Completion</span>
              <span className={styles.statValue}>{data.overall_completion}%</span>
            </div>
            <div className={styles.progressBar}>
              <div className={styles.progressFill} style={{ width: `${data.overall_completion}%` }}></div>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'right', marginTop: '0.25rem' }}>
              {data.completed_count} / {data.total_count} Completed
            </div>
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Weekly Streak</span>
              <span className={`${styles.statValue} ${styles.statFire}`}>
                {data.weekly_streak} Days 🔥
              </span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Avg Mock Score</span>
              <span className={`${styles.statValue} ${styles.statHighlight}`}>
                {data.mock_test_avg}%
              </span>
            </div>
          </div>
        </div>

        {/* Strengths & Weaknesses Card */}
        <div className={styles.sidebarCard}>
          <h3 className={styles.sidebarTitle}>
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
            Skill Profile
          </h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <span className={styles.statLabel}>Strengths</span>
            <div className={styles.pillContainer}>
              {data.strengths && data.strengths.length > 0 ? data.strengths.map((s: string, i: number) => (
                <span key={i} className={`${styles.pill} ${styles.pillGreen}`}>{s}</span>
              )) : <span className={styles.statLabel} style={{ fontSize: '0.8rem' }}>Needs more data</span>}
            </div>
          </div>
          
          <div>
            <span className={styles.statLabel}>Focus Areas</span>
            <div className={styles.pillContainer}>
              {data.weaknesses && data.weaknesses.length > 0 ? data.weaknesses.map((w: string, i: number) => (
                <span key={i} className={`${styles.pill} ${styles.pillRed}`}>{w}</span>
              )) : <span className={styles.statLabel} style={{ fontSize: '0.8rem' }}>None identified</span>}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

