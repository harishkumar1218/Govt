import React from 'react';
import styles from './Threads.module.css';

interface VoteControlProps {
  upvoteCount: number;
  hasUpvoted: boolean;
  onUpvote: (e: React.MouseEvent) => void;
  orientation?: 'vertical' | 'horizontal';
}

export default function VoteControl({
  upvoteCount,
  hasUpvoted,
  onUpvote,
  orientation = 'vertical',
}: VoteControlProps) {
  return (
    <div 
      className={`${styles.voteRail} ${orientation === 'horizontal' ? styles.voteRailHorizontal : ''}`}
      onClick={(e) => e.stopPropagation()} // Prevent card navigation trigger
    >
      <button
        className={`${styles.voteBtn} ${hasUpvoted ? styles.voteActive : ''}`}
        onClick={onUpvote}
        aria-pressed={hasUpvoted}
        aria-label={`Upvote doubt: current count ${upvoteCount}`}
      >
        ▲
      </button>
      <span className={styles.voteCount}>{upvoteCount}</span>
    </div>
  );
}
