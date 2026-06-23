import styles from './Threads.module.css';

interface ThreadsToolbarProps {
  search: string;
  setSearch: (value: string) => void;
  sort: string;
  setSort: (value: string) => void;
  category: string;
  setCategory: (value: string) => void;
  totalCount?: number;
  loading?: boolean;
}

export default function ThreadsToolbar({
  search,
  setSearch,
  sort,
  setSort,
  category,
  setCategory,
  totalCount,
  loading,
}: ThreadsToolbarProps) {
  const sortOptions = [
    { value: 'new', label: 'New' },
    { value: 'top', label: 'Top' },
    { value: 'most_answered', label: 'Most Answered' },
    { value: 'unanswered', label: 'Unanswered' },
    { value: 'solved', label: 'Solved' },
  ];

  const categories = [
    'All', 'Polity', 'Economy', 'History', 'Geography', 
    'Current Affairs', 'Essay', 'CSAT', 'Ethics', 'Optional'
  ];

  return (
    <div className={styles.feedControls}>
      <div className={styles.searchSortRow}>
        {/* Search Bar */}
        <div className={styles.searchContainer}>
          <svg className={styles.searchIcon} viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search doubts, topics, or keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search doubts"
          />
        </div>

        {/* Sort Segmented Control */}
        <div className={styles.sortSegmented} role="radiogroup" aria-label="Sort options">
          {sortOptions.map(opt => (
            <button
              key={opt.value}
              role="radio"
              aria-checked={sort === opt.value}
              className={`${styles.sortSegBtn} ${sort === opt.value ? styles.activeSortSegBtn : ''}`}
              onClick={() => setSort(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className={styles.categoryChipsContainer} aria-label="Category filters">
        {categories.map(cat => (
          <button
            key={cat}
            className={`${styles.categoryChip} ${category === cat ? styles.activeCategoryChip : ''}`}
            onClick={() => setCategory(cat)}
            aria-label={`Filter by ${cat}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Result Count and Loading Status */}
      {!loading && totalCount !== undefined && (
        <div className={styles.resultCountRow}>
          <span>{totalCount} {totalCount === 1 ? 'doubt' : 'doubts'} found</span>
        </div>
      )}
    </div>
  );
}
