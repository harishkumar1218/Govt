import { useState, useEffect, useCallback, useRef } from 'react';
import { ThreadsService } from '../../services/ThreadsService';
import type { Thread, ListThreadsParams } from '../../services/ThreadsService';
import { useDebouncedValue } from './useDebouncedValue';
import { useToast } from './ToastContext';

export interface UseThreadsFeedOptions {
  initialSort?: string;
  initialCategory?: string;
  initialSearch?: string;
  onUrlSync?: (params: { sort: string; category: string; search: string }) => void;
}

export function useThreadsFeed(options?: UseThreadsFeedOptions) {
  const { showToast } = useToast();
  
  // Read initial states
  const [sort, setSort] = useState(options?.initialSort || 'new');
  const [category, setCategory] = useState(options?.initialCategory || 'All');
  const [search, setSearch] = useState(options?.initialSearch || '');
  
  const debouncedSearch = useDebouncedValue(search, 300);

  const [threads, setThreads] = useState<Thread[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [hasMore, setHasMore] = useState(false);
  
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);

  // Keep track of pending actions to prevent double clicks
  const upvotingIds = useRef<Set<number>>(new Set());

  // URL syncing trigger
  useEffect(() => {
    if (options?.onUrlSync) {
      options.onUrlSync({ sort, category, search });
    }
  }, [sort, category, search, options]);

  const fetchThreads = useCallback(async (pageNum = 1, isLoadMore = false) => {
    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);

    const params: ListThreadsParams = {
      search: debouncedSearch.trim() || undefined,
      sort,
      category: category === 'All' ? undefined : category,
      page: pageNum,
      pageSize,
    };

    try {
      const data = await ThreadsService.listThreads(params);
      
      setThreads((prev) => (isLoadMore ? [...prev, ...data.results] : data.results));
      setTotalCount(data.totalCount);
      setPage(data.page);
      setHasMore(data.hasMore);
      
      // Increment sidebar stats reload key
      setSidebarRefreshKey((prev) => prev + 1);
    } catch (err: any) {
      setError(err.message || 'Failed to load threads. Please try again.');
      showToast(err.message || 'Failed to load threads.', 'error');
    } finally {
      setLoading(false);
      setLoadingMore(false);
      setIsRefreshing(false);
    }
  }, [debouncedSearch, sort, category, pageSize, showToast]);

  // Initial load or query change
  useEffect(() => {
    fetchThreads(1, false);
  }, [fetchThreads]);

  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;
    fetchThreads(page + 1, true);
  }, [page, hasMore, loadingMore, fetchThreads]);

  const refresh = useCallback(() => {
    setIsRefreshing(true);
    fetchThreads(1, false);
  }, [fetchThreads]);

  // Optimistic upvote
  const handleUpvote = useCallback(async (thread: Thread) => {
    if (upvotingIds.current.has(thread.id)) return;
    upvotingIds.current.add(thread.id);

    const previousState = {
      upvoteCount: thread.upvoteCount,
      hasCurrentUserUpvoted: thread.hasCurrentUserUpvoted,
    };

    const newHasUpvoted = !thread.hasCurrentUserUpvoted;
    const newUpvoteCount = newHasUpvoted 
      ? thread.upvoteCount + 1 
      : Math.max(0, thread.upvoteCount - 1);

    // Optimistically update list
    setThreads((prev) =>
      prev.map((t) =>
        t.id === thread.id
          ? { ...t, hasCurrentUserUpvoted: newHasUpvoted, upvoteCount: newUpvoteCount }
          : t
      )
    );

    try {
      if (newHasUpvoted) {
        await ThreadsService.upvoteThread(thread.id);
      } else {
        await ThreadsService.removeThreadUpvote(thread.id);
      }
      setSidebarRefreshKey((prev) => prev + 1);
    } catch (err) {
      // Roll back
      setThreads((prev) =>
        prev.map((t) => (t.id === thread.id ? { ...t, ...previousState } : t))
      );
      showToast('Failed to update upvote. Please try again.', 'error');
    } finally {
      upvotingIds.current.delete(thread.id);
    }
  }, [showToast]);

  const handleDelete = useCallback(async (threadId: number) => {
    try {
      await ThreadsService.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.id !== threadId));
      setTotalCount((prev) => Math.max(0, prev - 1));
      setSidebarRefreshKey((prev) => prev + 1);
      showToast('Doubt deleted successfully.', 'success');
    } catch (err) {
      showToast('Failed to delete doubt.', 'error');
    }
  }, [showToast]);

  return {
    threads,
    totalCount,
    loading,
    loadingMore,
    error,
    hasMore,
    sort,
    setSort,
    category,
    setCategory,
    search,
    setSearch,
    loadMore,
    refresh,
    isRefreshing,
    handleUpvote,
    handleDelete,
    sidebarRefreshKey,
  };
}
