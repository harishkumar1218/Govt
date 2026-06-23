import React from 'react';
import type { Thread } from '../../services/ThreadsService';
import VoteControl from './VoteControl';
import { useToast } from './ToastContext';
import styles from './Threads.module.css';

interface ThreadCardProps {
  thread: Thread;
  userId: number;
  onSelect: () => void;
  onUpvote: (e: React.MouseEvent) => void;
  onShare: (e: React.MouseEvent) => void;
  onEdit: (e: React.MouseEvent) => void;
  onDelete: (e: React.MouseEvent) => void;
}

export default function ThreadCard({
  thread,
  userId,
  onSelect,
  onUpvote,
  onShare,
  onEdit,
  onDelete,
}: ThreadCardProps) {
  const { showToast } = useToast();
  const isOwner = thread.authorId === userId;
  const showEdited = thread.createdAt !== thread.updatedAt;

  const handleReportClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    showToast('Reporting will be available soon.', 'info');
  };

  return (
    <div 
      className={`${styles.threadCard} ${thread.isSolved ? styles.solvedCard : ''}`}
      onClick={onSelect}
      role="article"
    >
      {/* Left Vote Rail */}
      <VoteControl
        upvoteCount={thread.upvoteCount}
        hasUpvoted={thread.hasCurrentUserUpvoted}
        onUpvote={onUpvote}
      />

      {/* Main Content Area */}
      <div className={styles.cardMainContent}>
        <div className={styles.cardHeader}>
          <div className={styles.headerLeftTags}>
            <span className={styles.tagChip}>{thread.category}</span>
            {thread.isSolved && (
              <span className={styles.solvedBadge} aria-label="Solved doubt badge">
                ✓ Solved
              </span>
            )}
          </div>
          
          <div className={styles.authorMeta}>
            <span>Posted by</span>
            <span className={styles.authorName}>u/{thread.authorName}</span>
            <span>&bull;</span>
            <span>
              {new Date(thread.createdAt).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short',
                year: 'numeric'
              })}
            </span>
            {showEdited && (
              <span className={styles.editedLabel} title="Edited">&bull; Edited</span>
            )}
          </div>
        </div>

        <h3 className={styles.cardTitle}>{thread.title}</h3>
        
        <p className={styles.cardBodyPreview}>
          {thread.body}
        </p>

        {/* Tags sub-row if present */}
        {thread.tags && thread.tags.length > 0 && (
          <div className={styles.tagsRow} aria-label="Post tags">
            {thread.tags.map(tag => (
              <span key={tag} className={styles.tagItem}>
                #{tag}
              </span>
            ))}
          </div>
        )}

        <div className={styles.cardFooter}>
          <div className={styles.footerLeft}>
            <span className={styles.actionBtn}>
              💬 {thread.answerCount} {thread.answerCount === 1 ? 'Reply' : 'Replies'}
              {thread.answerCount === 0 && (
                <span className={styles.unansweredText}> (Unanswered)</span>
              )}
            </span>

            <button 
              className={styles.actionBtn}
              onClick={onShare}
              aria-label="Share this doubt link"
            >
              <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18" cy="5" r="3"></circle>
                <circle cx="6" cy="12" r="3"></circle>
                <circle cx="18" cy="19" r="3"></circle>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
              </svg>
              Share
            </button>

            <button 
              className={styles.actionBtn}
              onClick={handleReportClick}
              aria-label="Report this post"
            >
              🚩 Report
            </button>
          </div>

          {isOwner && (
            <div className={styles.footerRight}>
              <button 
                className={styles.textBtn}
                onClick={onEdit}
                aria-label="Edit doubt post"
              >
                Edit
              </button>
              <button 
                className={`${styles.textBtn} ${styles.textBtnDanger}`}
                onClick={onDelete}
                aria-label="Delete doubt post"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
