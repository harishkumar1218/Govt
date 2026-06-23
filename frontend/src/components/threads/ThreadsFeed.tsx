import React from 'react';
import type { Thread } from '../../services/ThreadsService';
import { useThreadsFeed } from './useThreadsFeed';
import ThreadsSidebar from './ThreadsSidebar';
import ThreadsHeader from './ThreadsHeader';
import ThreadsToolbar from './ThreadsToolbar';
import ThreadCard from './ThreadCard';
import EmptyState from './EmptyState';
import SkeletonLoader from './SkeletonLoader';
import ErrorState from './ErrorState';
import styles from './Threads.module.css';

interface ThreadsFeedProps {
  userId: number;
  onSelectThread: (threadId: number) => void;
  onNewPostClick: () => void;
  onEditPostClick: (thread: Thread) => void;
  showToast?: (message: string) => void; // Optional fallback
}

export default function ThreadsFeed({
  userId,
  onSelectThread,
  onNewPostClick,
  onEditPostClick,
}: ThreadsFeedProps) {
  // Sync URL search params
  const getInitialParam = (key: string, fallback: string) => {
    return new URLSearchParams(window.location.search).get(key) || fallback;
  };

  const feed = useThreadsFeed({
    initialSort: getInitialParam('sort', 'new'),
    initialCategory: getInitialParam('category', 'All'),
    initialSearch: getInitialParam('search', ''),
    onUrlSync: ({ sort, category, search }) => {
      const params = new URLSearchParams(window.location.search);
      params.set('sort', sort);
      params.set('category', category);
      if (search.trim()) {
        params.set('search', search);
      } else {
        params.delete('search');
      }
      
      // Preserve threadId if it's there
      const threadId = new URLSearchParams(window.location.search).get('threadId');
      if (threadId) {
        params.set('threadId', threadId);
      }

      const newUrl = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState({}, '', newUrl);
    }
  });

  const handleCardClick = (threadId: number) => {
    onSelectThread(threadId);
  };

  const handleEditClick = (e: React.MouseEvent, thread: Thread) => {
    e.stopPropagation();
    onEditPostClick(thread);
  };

  const handleDeleteClick = (e: React.MouseEvent, threadId: number) => {
    e.stopPropagation();
    // Custom inline confirmations are handled on answers, 
    // for threads we use a clean confirm dialog to prevent accidental clicks.
    if (window.confirm('Are you sure you want to delete this doubt permanently?')) {
      feed.handleDelete(threadId);
    }
  };

  const handleShareClick = (e: React.MouseEvent, thread: Thread) => {
    e.stopPropagation();
    const shareUrl = `${window.location.origin}/?tab=threads&threadId=${thread.id}`;
    // Fallback clipboard copying
    navigator.clipboard.writeText(shareUrl).then(() => {
      // Toast notice will be handled inside the hook or shared triggers
    }).catch(() => {});
  };

  return (
    <div className={styles.threadsContainer}>
      {/* 1. Header */}
      <ThreadsHeader onNewPostClick={onNewPostClick} />

      {/* 2. Main Forum Layout */}
      <div className={styles.forumLayout}>
        {/* Left Column: Feed & Controls */}
        <div className={styles.feedColumn}>
          
          {/* Toolbar (Search, Sort, Category Chips) */}
          <ThreadsToolbar
            search={feed.search}
            setSearch={feed.setSearch}
            sort={feed.sort}
            setSort={feed.setSort}
            category={feed.category}
            setCategory={feed.setCategory}
            totalCount={feed.totalCount}
            loading={feed.loading}
          />

          {/* Manual/Pull style refresh button */}
          <div className={styles.refreshBar}>
            <button 
              className={styles.refreshBtn}
              onClick={feed.refresh}
              disabled={feed.loading || feed.isRefreshing}
              aria-label="Refresh doubts feed"
            >
              <svg 
                className={`${styles.refreshIcon} ${feed.isRefreshing ? styles.refreshSpin : ''}`} 
                viewBox="0 0 24 24" 
                width="14" 
                height="14" 
                stroke="currentColor" 
                strokeWidth="2.5" 
                fill="none"
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
              </svg>
              {feed.isRefreshing ? 'Refreshing...' : 'Refresh Feed'}
            </button>
          </div>

          {/* Feed Content States */}
          {feed.loading && feed.threads.length === 0 ? (
            <SkeletonLoader />
          ) : feed.error ? (
            <ErrorState message={feed.error} onRetry={feed.refresh} />
          ) : feed.threads.length === 0 ? (
            <EmptyState 
              isSearch={feed.search.trim().length > 0 || feed.category !== 'All'} 
              onAskDoubtClick={onNewPostClick} 
            />
          ) : (
            <>
              <div className={styles.threadsList}>
                {feed.threads.map((thread) => (
                  <ThreadCard
                    key={thread.id}
                    thread={thread}
                    userId={userId}
                    onSelect={() => handleCardClick(thread.id)}
                    onUpvote={(e) => {
                      e.stopPropagation();
                      feed.handleUpvote(thread);
                    }}
                    onShare={(e) => handleShareClick(e, thread)}
                    onEdit={(e) => handleEditClick(e, thread)}
                    onDelete={(e) => handleDeleteClick(e, thread.id)}
                  />
                ))}
              </div>

              {/* Load More Pagination */}
              {feed.hasMore && (
                <div className={styles.paginationRow}>
                  <button
                    className="btn btn-secondary"
                    onClick={feed.loadMore}
                    disabled={feed.loadingMore}
                    style={{ borderRadius: '100px', padding: '0.6rem 2rem', fontWeight: 600 }}
                  >
                    {feed.loadingMore ? 'Loading doubts...' : 'Load More Doubts'}
                  </button>
                </div>
              )}
            </>
          )}

        </div>

        {/* Right Column: Sidebar */}
        <ThreadsSidebar 
          activeCategory={feed.category} 
          onSelectCategory={feed.setCategory} 
          refreshTrigger={feed.sidebarRefreshKey} 
        />
      </div>
    </div>
  );
}
