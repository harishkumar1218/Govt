import type { Thread } from '../../services/ThreadsService';
import { useThreadDetail } from './useThreadDetail';
import { useClipboardShare } from './useClipboardShare';
import VoteControl from './VoteControl';
import AnswerComposer from './AnswerComposer';
import AnswerCard from './AnswerCard';
import ThreadsSidebar from './ThreadsSidebar';
import styles from './Threads.module.css';

interface ThreadDetailProps {
  threadId: number;
  userId: number;
  onBack: () => void;
  onDeleteThreadSuccess: () => void;
  onEditThreadClick: (thread: Thread) => void;
  showToast?: (message: string) => void; // Optional fallback
}

export default function ThreadDetail({
  threadId,
  userId,
  onBack,
  onDeleteThreadSuccess,
  onEditThreadClick,
}: ThreadDetailProps) {
  const detail = useThreadDetail(threadId, userId, onDeleteThreadSuccess);
  const { shareThread } = useClipboardShare();

  const handleShare = () => {
    if (detail.thread) {
      shareThread(detail.thread.id, detail.thread.title);
    }
  };

  const handleEditClick = () => {
    if (detail.thread) {
      onEditThreadClick(detail.thread);
    }
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this doubt permanently? This action cannot be undone.')) {
      detail.handleThreadDelete();
    }
  };

  if (detail.loading) {
    return (
      <div className={styles.statusContainer}>
        <div className={styles.loadingDots}><span/><span/><span/></div>
        <p style={{ marginTop: '1rem' }}>Loading doubt details...</p>
      </div>
    );
  }

  if (detail.error || !detail.thread) {
    return (
      <div className={styles.statusContainer}>
        <div className={styles.emptyIcon}>⚠️</div>
        <h3 className={styles.errorState}>{detail.error || 'Doubt thread not found.'}</h3>
        <button className="btn btn-secondary retryBtn" onClick={onBack}>
          &larr; Back to Feed
        </button>
      </div>
    );
  }

  const { thread } = detail;
  const isOwner = thread.authorId === userId;
  const showEdited = thread.createdAt !== thread.updatedAt;

  const visibleAnswers = (thread.answers || []).slice(0, detail.visibleAnswersCount);
  const remainingAnswersCount = (thread.answers || []).length - detail.visibleAnswersCount;

  return (
    <div className={styles.detailContainer}>
      <button className={styles.backBtn} onClick={onBack} aria-label="Back to doubts feed">
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to Threads
      </button>

      {/* Two column grid layout */}
      <div className={styles.forumLayout}>
        {/* Left Column: Post Details & Answers */}
        <div className={styles.feedColumn}>
          
          {/* Main Thread Card */}
          <article className={`${styles.detailCard} ${thread.isSolved ? styles.solvedCard : ''}`}>
            {/* Left Vote Rail */}
            <VoteControl
              upvoteCount={thread.upvoteCount}
              hasUpvoted={thread.hasCurrentUserUpvoted}
              onUpvote={detail.handleThreadUpvote}
            />

            <div className={styles.detailCardMain}>
              <div className={styles.detailHeader}>
                <div className={styles.headerLeftTags}>
                  <span className={styles.tagChip} style={{ display: 'inline-block' }}>
                    {thread.category}
                  </span>
                  {thread.isSolved && (
                    <span className={styles.solvedBadge} aria-label="Solved doubt badge">
                      ✓ Solved
                    </span>
                  )}
                </div>

                <h1 className={styles.detailTitle}>{thread.title}</h1>
                
                <div className={styles.authorMeta}>
                  <span>Posted by</span>
                  <span className={styles.authorName}>u/{thread.authorName}</span>
                  <span>&bull;</span>
                  <span>
                    {new Date(thread.createdAt).toLocaleDateString('en-IN', {
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
                  {thread.viewCount !== undefined && (
                    <>
                      <span>&bull;</span>
                      <span className={styles.viewsCount}>👁️ {thread.viewCount} views</span>
                    </>
                  )}
                </div>
              </div>

              <div className={styles.detailBody}>
                {thread.body}
              </div>

              {/* Tags sub-row if present */}
              {thread.tags && thread.tags.length > 0 && (
                <div className={styles.tagsRow} style={{ marginTop: '1.25rem', marginBottom: '0.5rem' }}>
                  {thread.tags.map(tag => (
                    <span key={tag} className={styles.tagItem}>
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              <div className={styles.detailFooter}>
                <div className={styles.footerLeft}>
                  <button className={styles.actionBtn} onClick={handleShare} aria-label="Share doubt post link">
                    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="18" cy="5" r="3"></circle>
                      <circle cx="6" cy="12" r="3"></circle>
                      <circle cx="18" cy="19" r="3"></circle>
                      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                    </svg>
                    Share
                  </button>

                  {/* Mark solved manually toggle for thread owner */}
                  {isOwner && (
                    <button
                      className={`${styles.actionBtn} ${thread.isSolved ? styles.solvedActionActive : ''}`}
                      onClick={detail.handleToggleSolved}
                      aria-label={thread.isSolved ? "Mark doubt unsolved" : "Mark doubt solved"}
                    >
                      ✓ {thread.isSolved ? 'Mark Unsolved' : 'Mark Solved'}
                    </button>
                  )}
                </div>

                {isOwner && (
                  <div className={styles.footerRight}>
                    <button className={styles.textBtn} onClick={handleEditClick} aria-label="Edit doubt details">Edit</button>
                    <button className={`${styles.textBtn} ${styles.textBtnDanger}`} onClick={handleDelete} aria-label="Delete doubt post">Delete</button>
                  </div>
                )}
              </div>
            </div>
          </article>

          {/* Quick Answer inline composer directly below post card */}
          <AnswerComposer
            value={detail.newAnswerBody}
            onChange={detail.setNewAnswerBody}
            onSubmit={detail.handleAnswerSubmit}
            isSubmitting={detail.isSubmittingAnswer}
          />

          {/* Answers list */}
          <section className={styles.answersSection}>
            <h2 className={styles.answersTitle}>
              {thread.answerCount} {thread.answerCount === 1 ? 'Answer' : 'Answers'}
              {thread.answerCount === 0 && (
                <span className={styles.unansweredText}> (Unanswered)</span>
              )}
            </h2>

            {thread.answers && thread.answers.length > 0 ? (
              <div className={styles.answersThreadWrapper}>
                <div className={styles.threadLine}></div>
                
                <div className={styles.answersList}>
                  {visibleAnswers.map((answer) => (
                    <AnswerCard
                      key={answer.id}
                      answer={answer}
                      userId={userId}
                      threadOwnerId={thread.authorId}
                      onUpvote={() => detail.handleAnswerUpvote(answer)}
                      onDelete={() => detail.handleAnswerDelete(answer.id)}
                      onAccept={() => detail.handleAcceptAnswer(answer.id)}
                      isEditing={detail.editingAnswerId === answer.id}
                      editingBody={detail.editingAnswerBody}
                      setEditingBody={detail.setEditingAnswerBody}
                      isSavingEdit={detail.isSavingAnswerEdit}
                      onStartEdit={() => detail.startEditingAnswer(answer)}
                      onCancelEdit={detail.cancelEditingAnswer}
                      onSaveEdit={() => detail.handleAnswerEditSave(answer.id)}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className={styles.emptyState} style={{ padding: '3rem 2rem' }}>
                <div className={styles.emptyIcon}>💬</div>
                <h3>No answers yet</h3>
                <p>Be the first to answer this question and help others in their preparation!</p>
              </div>
            )}

            {/* Pagination for answers */}
            {remainingAnswersCount > 0 && (
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1.5rem' }}>
                <button
                  className="btn btn-secondary"
                  onClick={detail.loadMoreAnswers}
                  style={{ borderRadius: '100px', padding: '0.5rem 1.5rem', fontWeight: 600 }}
                >
                  Show more answers ({remainingAnswersCount} remaining)
                </button>
              </div>
            )}
          </section>

        </div>

        {/* Right Column: Sidebar */}
        <ThreadsSidebar 
          activeCategory={thread.category}
          refreshTrigger={detail.sidebarRefreshKey}
        />
      </div>
    </div>
  );
}
