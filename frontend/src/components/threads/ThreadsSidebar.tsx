import { useState, useEffect } from 'react';
import { ThreadsService } from '../../services/ThreadsService';
import type { ThreadStats } from '../../services/ThreadsService';
import styles from './Threads.module.css';

interface ThreadsSidebarProps {
  activeCategory?: string;
  onSelectCategory?: (category: string) => void;
  refreshTrigger?: number;
}

export default function ThreadsSidebar({
  activeCategory = 'All',
  onSelectCategory,
  refreshTrigger = 0,
}: ThreadsSidebarProps) {
  const [stats, setStats] = useState<ThreadStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = () => {
    ThreadsService.getStats()
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch thread stats', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchStats();
  }, [refreshTrigger]);

  const categories = ['Polity', 'Economy', 'History', 'Geography', 'Current Affairs', 'Essay', 'CSAT', 'General'];

  return (
    <aside className={styles.sidebar}>
      {/* 1. Community Card */}
      <div className={styles.sidebarPanel}>
        <h3>UPSC Threads</h3>
        <p>A focused space for doubts, explanations, and peer learning for UPSC aspirants.</p>
        
        {loading ? (
          <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>Loading community stats...</div>
        ) : stats ? (
          <div className={styles.statsGrid}>
            <div className={styles.statBox}>
              <div className={styles.statNumber}>{stats.totalThreads}</div>
              <div className={styles.statLabel}>Doubts</div>
            </div>
            <div className={styles.statBox}>
              <div className={styles.statNumber}>{stats.totalAnswers}</div>
              <div className={styles.statLabel}>Replies</div>
            </div>
          </div>
        ) : (
          <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>Stats currently unavailable</div>
        )}
      </div>

      {/* 2. Posting Tips */}
      <div className={styles.sidebarPanel}>
        <h3>Posting Guidelines</h3>
        <ul className={styles.tipsList}>
          <li>
            <strong>Use a clear title:</strong> Summarize your specific question or topic.
          </li>
          <li>
            <strong>Add context:</strong> Provide the background, source paper, or book reference.
          </li>
          <li>
            <strong>Mention subject:</strong> Tag the correct GS paper or category for faster answers.
          </li>
        </ul>
      </div>

      {/* 3. Popular Categories */}
      <div className={styles.sidebarPanel}>
        <h3>Categories</h3>
        <div className={styles.sidebarTags}>
          <div 
            className={`${styles.sidebarTagItem} ${activeCategory === 'All' ? styles.activeSidebarTag : ''}`}
            onClick={() => onSelectCategory?.('All')}
          >
            <div className={styles.sidebarTagLeft}>
              <span>📁</span>
              <span>All Subjects</span>
            </div>
            {stats && (
              <span className={styles.sidebarTagCount}>
                {stats.totalThreads}
              </span>
            )}
          </div>
          
          {categories.map(cat => {
            const count = stats?.categoryCounts?.[cat] ?? 0;
            return (
              <div 
                key={cat}
                className={`${styles.sidebarTagItem} ${activeCategory === cat ? styles.activeSidebarTag : ''}`}
                onClick={() => onSelectCategory?.(cat)}
              >
                <div className={styles.sidebarTagLeft}>
                  <span>🏷️</span>
                  <span>{cat}</span>
                </div>
                <span className={styles.sidebarTagCount}>{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
