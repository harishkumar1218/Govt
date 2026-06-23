import { useState } from 'react';
import type { Answer } from '../../services/ThreadsService';
import { useToast } from './ToastContext';
import styles from './Threads.module.css';

interface AnswerCardProps {
  answer: Answer;
  userId: number;
  threadOwnerId: number;
  onUpvote: () => void;
  onDelete: () => void;
  onAccept: () => void;
  isEditing: boolean;
  editingBody: string;
  setEditingBody: (val: string) => void;
  isSavingEdit: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
}

export default function AnswerCard({
  answer,
  userId,
  threadOwnerId,
  onUpvote,
  onDelete,
  onAccept,
  isEditing,
  editingBody,
  setEditingBody,
  isSavingEdit,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
}: AnswerCardProps) {
  const { showToast } = useToast();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const isAnswerOwner = answer.authorId === userId;
  const isThreadOwner = threadOwnerId === userId;
  const showEdited = answer.createdAt !== answer.updatedAt;

  const handleReportClick = () => {
    showToast('Reporting will be available soon.', 'info');
  };

  const handleConfirmDelete = () => {
    onDelete();
    setShowDeleteConfirm(false);
  };

  const editLength = editingBody.trim().length;
  const isEditValid = editLength >= 10 && editLength <= 2000;

  return (
    <div className={`${styles.answerCard} ${answer.isAccepted ? styles.acceptedAnswerCard : ''}`} role="comment">
      {isEditing ? (
        <div className={styles.answerEditContainer}>
          <textarea
            className={styles.answerTextarea}
            value={editingBody}
            onChange={(e) => setEditingBody(e.target.value)}
            disabled={isSavingEdit}
            required
            aria-describedby="answer-edit-char-count"
          />
          <div className={styles.editActionsRow}>
            <span id="answer-edit-char-count" className={`${styles.charCount} ${editingBody.length > 2000 ? styles.charCountError : ''}`} style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {editingBody.length}/2000
            </span>
            <div className={styles.editActions}>
              <button
                className="btn btn-secondary"
                onClick={onCancelEdit}
                disabled={isSavingEdit}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={onSaveEdit}
                disabled={isSavingEdit || !isEditValid}
              >
                {isSavingEdit ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className={styles.answerHeader}>
            <div className={styles.authorMeta}>
              <div 
                className={styles.authorAvatar} 
                style={{ 
                  background: answer.isAccepted 
                    ? 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)'
                    : 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)', 
                  color: answer.isAccepted ? '#2563eb' : '#16a34a' 
                }}
              >
                {answer.authorName.slice(0, 2).toUpperCase()}
              </div>
              <span className={styles.authorName}>u/{answer.authorName}</span>
              <span>&bull;</span>
              <span>
                {new Date(answer.createdAt).toLocaleDateString('en-IN', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </span>
              {showEdited && (
                <span className={styles.editedLabel} title="Edited">&bull; Edited</span>
              )}
            </div>

            {/* Accepted Answer Badge */}
            {answer.isAccepted && (
              <span className={styles.acceptedLabel} aria-label="Accepted solution badge">
                ✓ Accepted Solution
              </span>
            )}
          </div>

          <div className={styles.answerBody}>
            {answer.body}
          </div>

          <div className={styles.answerFooter}>
            <div className={styles.footerLeft}>
              <button
                className={`${styles.actionBtn} ${answer.hasCurrentUserUpvoted ? styles.upvoted : ''}`}
                onClick={onUpvote}
                aria-pressed={answer.hasCurrentUserUpvoted}
                aria-label={`Upvote reply: current count ${answer.upvoteCount}`}
              >
                <span>▲</span> {answer.upvoteCount}
              </button>

              {/* Accept solution button for thread owner */}
              {isThreadOwner && (
                <button
                  className={`${styles.actionBtn} ${answer.isAccepted ? styles.acceptedActionActive : ''}`}
                  onClick={onAccept}
                  aria-label={answer.isAccepted ? "Unaccept this solution" : "Accept this solution"}
                >
                  ✓ {answer.isAccepted ? 'Unaccept Solution' : 'Accept Solution'}
                </button>
              )}

              <button 
                className={styles.actionBtn}
                onClick={handleReportClick}
                aria-label="Report answer"
              >
                🚩 Report
              </button>
            </div>

            {/* Edit/Delete triggers */}
            {isAnswerOwner && (
              <div className={styles.footerRight}>
                {showDeleteConfirm ? (
                  <div className={styles.inlineConfirm} role="alert">
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-danger)', marginRight: '0.5rem', fontWeight: 600 }}>Delete permanently?</span>
                    <button className={`${styles.textBtn} ${styles.textBtnDanger}`} onClick={handleConfirmDelete} aria-label="Confirm deletion">Delete</button>
                    <button className={styles.textBtn} onClick={() => setShowDeleteConfirm(false)} aria-label="Cancel deletion">Cancel</button>
                  </div>
                ) : (
                  <>
                    <button className={styles.textBtn} onClick={onStartEdit} aria-label="Edit answer">Edit</button>
                    <button className={`${styles.textBtn} ${styles.textBtnDanger}`} onClick={() => setShowDeleteConfirm(true)} aria-label="Delete answer">Delete</button>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
