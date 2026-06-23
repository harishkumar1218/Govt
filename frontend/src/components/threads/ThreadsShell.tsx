import { useState, useEffect } from 'react';
import ThreadsFeed from './ThreadsFeed';
import ThreadDetail from './ThreadDetail';
import ThreadComposerModal from './ThreadComposerModal';
import { ThreadsService } from '../../services/ThreadsService';
import type { Thread } from '../../services/ThreadsService';
import { useToast } from './ToastContext';
import styles from './Threads.module.css';

interface ThreadsShellProps {
  userId: number;
}

export default function ThreadsShell({ userId }: ThreadsShellProps) {
  const { showToast } = useToast();
  
  // URL state synchronization
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  
  // Modal composition states
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const [editingThread, setEditingThread] = useState<Thread | null>(null);
  const [refreshSeed, setRefreshSeed] = useState(0);

  // Load state from URL initially and on popstate changes
  useEffect(() => {
    const handleUrlChange = () => {
      const params = new URLSearchParams(window.location.search);
      const threadIdParam = params.get('threadId');
      if (threadIdParam) {
        setSelectedThreadId(Number(threadIdParam));
      } else {
        setSelectedThreadId(null);
      }
    };

    handleUrlChange(); // initial check
    window.addEventListener('popstate', handleUrlChange);
    return () => window.removeEventListener('popstate', handleUrlChange);
  }, []);

  const updateUrl = (threadId: number | null) => {
    const params = new URLSearchParams(window.location.search);
    if (threadId !== null) {
      params.set('threadId', String(threadId));
    } else {
      params.delete('threadId');
    }
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.pushState({}, '', newUrl);
  };

  const handleSelectThread = (id: number) => {
    setSelectedThreadId(id);
    updateUrl(id);
  };

  const handleBackToFeed = () => {
    setSelectedThreadId(null);
    updateUrl(null);
    setRefreshSeed(prev => prev + 1); // trigger reload on feed
  };

  const handleComposerSubmit = async (title: string, body: string, category: string, tags: string[]) => {
    try {
      if (editingThread) {
        await ThreadsService.updateThread(editingThread.id, title, body, category, tags);
        showToast('Doubt updated successfully.', 'success');
        setEditingThread(null);
        setRefreshSeed(prev => prev + 1);
      } else {
        await ThreadsService.createThread(title, body, category, tags);
        showToast('Doubt posted successfully!', 'success');
        setRefreshSeed(prev => prev + 1);
      }
    } catch (err: any) {
      throw new Error(err.message || 'Failed to submit doubt.');
    }
  };

  const handleEditThreadClick = (thread: Thread) => {
    setEditingThread(thread);
    setIsComposerOpen(true);
  };

  const handleNewPostClick = () => {
    setEditingThread(null);
    setIsComposerOpen(true);
  };

  return (
    <div className={styles.threadsShell}>
      {selectedThreadId !== null ? (
        <ThreadDetail
          key={`detail-${selectedThreadId}-${refreshSeed}`}
          threadId={selectedThreadId}
          userId={userId}
          onBack={handleBackToFeed}
          onDeleteThreadSuccess={handleBackToFeed}
          onEditThreadClick={handleEditThreadClick}
        />
      ) : (
        <ThreadsFeed
          key={`feed-${refreshSeed}`}
          userId={userId}
          onSelectThread={handleSelectThread}
          onNewPostClick={handleNewPostClick}
          onEditPostClick={handleEditThreadClick}
        />
      )}

      {/* Shared composer modal */}
      <ThreadComposerModal
        isOpen={isComposerOpen}
        onClose={() => {
          setIsComposerOpen(false);
          setEditingThread(null);
        }}
        onSubmit={handleComposerSubmit}
        initialTitle={editingThread?.title || ''}
        initialBody={editingThread?.body || ''}
        initialCategory={editingThread?.category || 'General'}
        initialTags={editingThread?.tags || []}
        isEditMode={!!editingThread}
      />
    </div>
  );
}
