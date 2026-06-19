import { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './CurrentAffairsPage.module.css';

interface NewsItem {
  id: string;
  title: string;
  link: string;
  description: string;
  published: string;
  image?: string;
}

interface ArchiveArticle {
  title: string;
  description: string;
  date: string;
  source: string;
  link: string;
}

interface MonthData {
  monthName: string;
  articles: ArchiveArticle[];
}

interface YearArchive {
  year: number;
  summary: string;
  highlights: string[];
  months: MonthData[];
}

interface Props {
  onBack: () => void;
}


export default function CurrentAffairsPage({ onBack }: Props) {
  const [todayNews, setTodayNews] = useState<NewsItem[]>([]);
  const [olderNews, setOlderNews] = useState<NewsItem[]>([]);
  const [archives, setArchives] = useState<YearArchive[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Archive States
  const [activeView, setActiveView] = useState<'latest' | 'archive'>('latest');
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  useEffect(() => {
    fetch(apiUrl('/api/current-affairs/'))
      .then(res => {
        if (!res.ok) throw new Error("Failed to fetch current affairs.");
        return res.json();
      })
      .then(data => {
        setTodayNews(data.today || []);
        setOlderNews(data.older || []);
        setArchives(data.archive || []);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return isoString;
    }
  };

  const handleReadMoreYear = (year: number) => {
    setSelectedYear(year);
    setActiveView('archive');
  };

  const selectedYearData = archives.find(archive => archive.year === selectedYear);

  if (loading) {
    return (
      <div className={`container ${styles.pageWrapper}`}>
        <div className={styles.loadingWrapper}>
          <div className="spinner" style={{ width: '40px', height: '40px', border: '4px solid var(--border)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Gathering latest national intelligence...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`container ${styles.pageWrapper}`}>
        <div className={styles.loadingWrapper}>
          <h2 style={{ color: 'var(--danger)' }}>Connection Intercepted</h2>
          <p style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>{error}</p>
          <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={onBack}>Return to Base</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`container ${styles.pageWrapper}`}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            {activeView === 'latest' ? 'The Daily Intel' : `${selectedYear} Intelligence Archive`}
          </h1>
          <p className={styles.subtitle}>
            {activeView === 'latest' 
              ? 'Curated national affairs for your civil services preparation.' 
              : `Reviewing month-by-month historical records for the year ${selectedYear}.`}
          </p>
        </div>
        <div>
          {activeView === 'archive' ? (
            <button className={styles.backBtn} onClick={() => setActiveView('latest')} id="btn-back-intel">
              ← Return to Daily Intel
            </button>
          ) : (
            <button className={styles.backBtn} onClick={onBack} id="btn-back-dashboard">
              ← Back to Dashboard
            </button>
          )}
        </div>
      </header>

      {activeView === 'latest' ? (
        <div className={styles.contentSplit}>
          {/* Left Column: Chronological Timeline of Years */}
          <aside className={styles.timelineColumn}>
            <h2 className={styles.columnTitle}>Historical Intel</h2>
            <div className={styles.timelineContainer}>
              <div className={styles.verticalLine}></div>
              
              {archives.map((archive) => (
                <div className={styles.timelineItem} key={archive.year}>
                  <div className={styles.timelineNode}></div>
                  <div className={styles.yearCard}>
                    <div className={styles.yearHeader}>
                      <span className={styles.yearBadge}>{archive.year}</span>
                    </div>
                    <p className={styles.yearSummary}>{archive.summary}</p>
                    <ul className={styles.yearHighlights}>
                      {archive.highlights.slice(0, 4).map((hl, idx) => (
                        <li key={idx}>{hl}</li>
                      ))}
                    </ul>
                    <button 
                      className={styles.readMoreYearBtn} 
                      onClick={() => handleReadMoreYear(archive.year)}
                      id={`btn-explore-${archive.year}`}
                    >
                      Read More News ({archive.year}) →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </aside>

          {/* Right Column: Live Current Affairs Feed */}
          <div className={styles.newsColumn}>
            <h2 className={styles.columnTitle}>Real-Time Intelligence</h2>
            {todayNews.length > 0 && (
              <section>
                <h3 className={styles.sectionTitle}>
                  <span className={styles.todayIcon}>●</span> Today's Top Stories
                </h3>
                <div className={styles.newsGrid}>
                  {todayNews.map(item => (
                    <a href={item.link} target="_blank" rel="noreferrer" className={styles.newsCard} key={item.id} id={`news-today-${item.id}`}>
                      <div className={styles.cardDate}>{formatDate(item.published)}</div>
                      <h4 className={styles.cardTitle}>{item.title}</h4>
                      <p className={styles.cardDesc}>{item.description}</p>
                      <div className={styles.readMore}>Read Full Report →</div>
                    </a>
                  ))}
                </div>
              </section>
            )}

            {olderNews.length > 0 && (
              <section>
                <h3 className={styles.sectionTitle}>Recent Archives</h3>
                <div className={styles.newsGrid}>
                  {olderNews.map(item => (
                    <a href={item.link} target="_blank" rel="noreferrer" className={styles.newsCard} key={item.id} id={`news-older-${item.id}`}>
                      <div className={styles.cardDate}>{formatDate(item.published)}</div>
                      <h4 className={styles.cardTitle}>{item.title}</h4>
                      <p className={styles.cardDesc}>{item.description}</p>
                      <div className={styles.readMore}>Read Full Report →</div>
                    </a>
                  ))}
                </div>
              </section>
            )}

            {todayNews.length === 0 && olderNews.length === 0 && (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                No active real-time intelligence available. Use the left column archives to review historical news.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Yearly Month-Wise Archive View */
        <div className={styles.archiveWrapper}>
          {selectedYearData ? (
            <div className={styles.monthTimeline}>
              <div className={styles.archiveVerticalLine}></div>
              
              {selectedYearData.months.map((month, mIdx) => (
                <div className={styles.monthSection} key={mIdx}>
                  <div className={styles.monthTimelineNode}></div>
                  <div className={styles.monthHeader}>
                    <span className={styles.monthBadge}>{month.monthName}</span>
                    <span className={styles.articleCount}>{month.articles.length} Reports</span>
                  </div>
                  
                  <div className={styles.archiveGrid}>
                    {month.articles.map((art, aIdx) => (
                      <a 
                        href={art.link} 
                        target="_blank" 
                        rel="noreferrer" 
                        className={styles.archiveCard} 
                        key={aIdx} 
                        id={`archive-item-${selectedYear}-${mIdx}-${aIdx}`}
                      >
                        <div className={styles.archiveCardHeader}>
                          <span className={styles.archiveSource}>{art.source}</span>
                          <span className={styles.archiveDate}>{formatDate(art.date)}</span>
                        </div>
                        <h3 className={styles.archiveCardTitle}>{art.title}</h3>
                        <p className={styles.archiveCardDesc}>{art.description}</p>
                        <div className={styles.archiveReadMore}>Read Full Report →</div>
                      </a>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              No data found for year {selectedYear}.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
