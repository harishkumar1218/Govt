import { useState, useEffect, useCallback, useRef } from 'react';
import { ThreadsService } from '../../services/ThreadsService';
import type { Thread, Answer } from '../../services/ThreadsService';
import { useToast } from './ToastContext';

export function useThreadDetail(threadId: number, userId: number, onDeleteSuccess?: () => void) {
  const { showToast } = useToast();

  const [thread, setThread] = useState<Thread | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination for visible answers (initial 4, load 10 more)
  const [visibleAnswersCount, setVisibleAnswersCount] = useState(4);

  // Answer composer states
  const [newAnswerBody, setNewAnswerBody] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [composerCooldown, setComposerCooldown] = useState(false);

  // Inline editing answer state
  const [editingAnswerId, setEditingAnswerId] = useState<number | null>(null);
  const [editingAnswerBody, setEditingAnswerBody] = useState('');
  const [isSavingAnswerEdit, setIsSavingAnswerEdit] = useState(false);

  // Sidebar refresh key trigger
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);

  // Double click protection
  const isUpvoting = useRef(false);
  const isMutatingAnswer = useRef(new Set<number>());

  const fetchThreadDetails = useCallback(async () => {
    setLoading(true);
    try {
      const data = await ThreadsService.getThreadById(threadId);
      setThread(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load thread details.');
      showToast(err.message || 'Failed to load thread details.', 'error');
    } finally {
      setLoading(false);
    }
  }, [threadId, showToast]);

  useEffect(() => {
    fetchThreadDetails();
    setVisibleAnswersCount(4); // Reset on ID change
  }, [fetchThreadDetails]);

  // Optimistic Thread upvote
  const handleThreadUpvote = useCallback(async () => {
    if (!thread || isUpvoting.current) return;
    isUpvoting.current = true;

    const previousState = {
      upvoteCount: thread.upvoteCount,
      hasCurrentUserUpvoted: thread.hasCurrentUserUpvoted,
    };

    const newHasUpvoted = !thread.hasCurrentUserUpvoted;
    const newUpvoteCount = newHasUpvoted 
      ? thread.upvoteCount + 1 
      : Math.max(0, thread.upvoteCount - 1);

    setThread((prev) => prev ? { ...prev, hasCurrentUserUpvoted: newHasUpvoted, upvoteCount: newUpvoteCount } : null);

    try {
      if (newHasUpvoted) {
        await ThreadsService.upvoteThread(thread.id);
      } else {
        await ThreadsService.removeThreadUpvote(thread.id);
      }
      setSidebarRefreshKey((prev) => prev + 1);
    } catch (err) {
      setThread((prev) => prev ? { ...prev, ...previousState } : null);
      showToast('Failed to update upvote.', 'error');
    } finally {
      isUpvoting.current = false;
    }
  }, [thread, showToast]);

  const handleThreadDelete = useCallback(async () => {
    if (!thread) return;
    try {
      await ThreadsService.deleteThread(thread.id);
      showToast('Doubt deleted successfully.', 'success');
      if (onDeleteSuccess) onDeleteSuccess();
    } catch (err) {
      showToast('Failed to delete doubt.', 'error');
    }
  }, [thread, showToast, onDeleteSuccess]);

  // Solved toggle directly (without accepted answer)
  const handleToggleSolved = useCallback(async () => {
    if (!thread) return;
    const targetSolved = !thread.isSolved;
    
    try {
      const updated = await ThreadsService.updateThread(thread.id, thread.title, thread.body, thread.category, thread.tags, targetSolved);
      setThread((prev) => prev ? { ...prev, isSolved: updated.isSolved } : null);
      setSidebarRefreshKey((prev) => prev + 1);
      showToast(targetSolved ? 'Doubt marked as solved.' : 'Doubt marked as unsolved.', 'success');
    } catch (err) {
      showToast('Failed to update doubt state.', 'error');
    }
  }, [thread, showToast]);

  // Answer flow
  const handleAnswerSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!thread) return;
    if (composerCooldown) {
      showToast('Please wait a moment before sending another answer.', 'info');
      return;
    }

    const trimmedBody = newAnswerBody.trim();
    if (!trimmedBody) return;
    if (trimmedBody.length < 10) {
      showToast('Answer must be at least 10 characters.', 'error');
      return;
    }
    if (trimmedBody.length > 2000) {
      showToast('Answer cannot exceed 2000 characters.', 'error');
      return;
    }

    setIsSubmittingAnswer(true);
    try {
      const created = await ThreadsService.createAnswer(thread.id, trimmedBody);
      setThread((prev) => {
        if (!prev) return null;
        const currentAnswers = prev.answers ? [...prev.answers] : [];
        // Insert created answer, ensuring accepted answer remains pinned first
        const updated = [...currentAnswers, created];
        
        // Sort remaining
        const acceptedId = prev.acceptedAnswerId;
        updated.sort((a, b) => b.upvoteCount - a.upvoteCount);
        
        if (acceptedId) {
          const acceptedIdx = updated.findIndex(a => a.id === acceptedId);
          if (acceptedIdx > -1) {
            const acc = updated.splice(acceptedIdx, 1)[0];
            updated.unshift(acc);
          }
        }
        return {
          ...prev,
          answerCount: prev.answerCount + 1,
          answers: updated,
        };
      });

      setNewAnswerBody('');
      setSidebarRefreshKey((prev) => prev + 1);
      showToast('Answer posted successfully!', 'success');

      // Rate limit composer cooldown for 3 seconds
      setComposerCooldown(true);
      setTimeout(() => setComposerCooldown(false), 3000);
    } catch (err: any) {
      showToast(err.message || 'Failed to submit answer.', 'error');
    } finally {
      setIsSubmittingAnswer(false);
    }
  }, [thread, newAnswerBody, composerCooldown, showToast]);

  // Optimistic Answer upvote
  const handleAnswerUpvote = useCallback(async (answer: Answer) => {
    if (!thread || !thread.answers || isMutatingAnswer.current.has(answer.id)) return;
    isMutatingAnswer.current.add(answer.id);

    const previousState = {
      upvoteCount: answer.upvoteCount,
      hasCurrentUserUpvoted: answer.hasCurrentUserUpvoted,
    };

    const newHasUpvoted = !answer.hasCurrentUserUpvoted;
    const newUpvoteCount = newHasUpvoted 
      ? answer.upvoteCount + 1 
      : Math.max(0, answer.upvoteCount - 1);

    setThread((prev) => {
      if (!prev || !prev.answers) return prev;
      let updated = prev.answers.map((a) =>
        a.id === answer.id ? { ...a, hasCurrentUserUpvoted: newHasUpvoted, upvoteCount: newUpvoteCount } : a
      );
      
      // Sort
      const acceptedId = prev.acceptedAnswerId;
      updated.sort((a, b) => b.upvoteCount - a.upvoteCount);
      if (acceptedId) {
        const acceptedIdx = updated.findIndex(a => a.id === acceptedId);
        if (acceptedIdx > -1) {
          const acc = updated.splice(acceptedIdx, 1)[0];
          updated.unshift(acc);
        }
      }
      return { ...prev, answers: updated };
    });

    try {
      if (newHasUpvoted) {
        await ThreadsService.upvoteAnswer(answer.id);
      } else {
        await ThreadsService.removeAnswerUpvote(answer.id);
      }
      setSidebarRefreshKey((prev) => prev + 1);
    } catch (err) {
      setThread((prev) => {
        if (!prev || !prev.answers) return prev;
        let reverted = prev.answers.map((a) => (a.id === answer.id ? { ...a, ...previousState } : a));
        
        const acceptedId = prev.acceptedAnswerId;
        reverted.sort((a, b) => b.upvoteCount - a.upvoteCount);
        if (acceptedId) {
          const acceptedIdx = reverted.findIndex(a => a.id === acceptedId);
          if (acceptedIdx > -1) {
            const acc = reverted.splice(acceptedIdx, 1)[0];
            reverted.unshift(acc);
          }
        }
        return { ...prev, answers: reverted };
      });
      showToast('Failed to update answer upvote.', 'error');
    } finally {
      isMutatingAnswer.current.delete(answer.id);
    }
  }, [thread, showToast]);

  const handleAnswerDelete = useCallback(async (answerId: number) => {
    if (!thread) return;
    try {
      await ThreadsService.deleteAnswer(answerId);
      setThread((prev) => {
        if (!prev) return null;
        const filtered = prev.answers ? prev.answers.filter((a) => a.id !== answerId) : [];
        const wasAccepted = prev.acceptedAnswerId === answerId;
        return {
          ...prev,
          answerCount: Math.max(0, prev.answerCount - 1),
          answers: filtered,
          acceptedAnswerId: wasAccepted ? null : prev.acceptedAnswerId,
          isSolved: wasAccepted ? false : prev.isSolved,
        };
      });
      setSidebarRefreshKey((prev) => prev + 1);
      showToast('Answer deleted.', 'success');
    } catch (err) {
      showToast('Failed to delete answer.', 'error');
    }
  }, [thread, showToast]);

  const startEditingAnswer = useCallback((answer: Answer) => {
    setEditingAnswerId(answer.id);
    setEditingAnswerBody(answer.body);
  }, []);

  const cancelEditingAnswer = useCallback(() => {
    setEditingAnswerId(null);
    setEditingAnswerBody('');
  }, []);

  const handleAnswerEditSave = useCallback(async (answerId: number) => {
    const trimmedEdit = editingAnswerBody.trim();
    if (!trimmedEdit) return;
    if (trimmedEdit.length < 10) {
      showToast('Answer edit must be at least 10 characters.', 'error');
      return;
    }
    if (trimmedEdit.length > 2000) {
      showToast('Answer edit cannot exceed 2000 characters.', 'error');
      return;
    }

    setIsSavingAnswerEdit(true);
    try {
      const updated = await ThreadsService.updateAnswer(answerId, trimmedEdit);
      setThread((prev) => {
        if (!prev || !prev.answers) return prev;
        let updatedList = prev.answers.map((a) => (a.id === answerId ? updated : a));
        
        const acceptedId = prev.acceptedAnswerId;
        updatedList.sort((a, b) => b.upvoteCount - a.upvoteCount);
        if (acceptedId) {
          const acceptedIdx = updatedList.findIndex(a => a.id === acceptedId);
          if (acceptedIdx > -1) {
            const acc = updatedList.splice(acceptedIdx, 1)[0];
            updatedList.unshift(acc);
          }
        }
        return { ...prev, answers: updatedList };
      });
      cancelEditingAnswer();
      showToast('Answer updated successfully.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to update answer.', 'error');
    } finally {
      setIsSavingAnswerEdit(false);
    }
  }, [editingAnswerBody, showToast, cancelEditingAnswer]);

  // Answer acceptance flow (solved badge & pin answer)
  const handleAcceptAnswer = useCallback(async (answerId: number) => {
    if (!thread) return;
    const isCurrentlyAccepted = thread.acceptedAnswerId === answerId;

    try {
      if (isCurrentlyAccepted) {
        // Toggle off
        const data = await ThreadsService.unacceptAnswer(thread.id, answerId);
        setThread((prev) => {
          if (!prev || !prev.answers) return prev;
          
          // Set isSolved=False, acceptedAnswerId=null, and unaccept answer item
          const updatedAnswers = prev.answers.map((a) =>
            a.id === answerId ? { ...a, isAccepted: false } : a
          );
          
          // Re-sort answers by votes since it's no longer pinned
          updatedAnswers.sort((a, b) => b.upvoteCount - a.upvoteCount);
          
          return {
            ...prev,
            isSolved: data.isSolved,
            acceptedAnswerId: data.acceptedAnswerId,
            answers: updatedAnswers,
          };
        });
        showToast('Answer unaccepted. Doubt is no longer solved.', 'success');
      } else {
        // Toggle on
        const data = await ThreadsService.acceptAnswer(thread.id, answerId);
        setThread((prev) => {
          if (!prev || !prev.answers) return prev;
          
          // Set isSolved=True, acceptedAnswerId=answerId, and set accept status on answer item
          const updatedAnswers = prev.answers.map((a) =>
            a.id === answerId ? { ...a, isAccepted: true } : { ...a, isAccepted: false }
          );
          
          // Sort remaining, placing the newly accepted first (pinned)
          updatedAnswers.sort((a, b) => b.upvoteCount - a.upvoteCount);
          const accIdx = updatedAnswers.findIndex(a => a.id === answerId);
          if (accIdx > -1) {
            const acc = updatedAnswers.splice(accIdx, 1)[0];
            updatedAnswers.unshift(acc);
          }

          return {
            ...prev,
            isSolved: data.isSolved,
            acceptedAnswerId: data.acceptedAnswerId,
            answers: updatedAnswers,
          };
        });
        showToast('Answer accepted as the solution!', 'success');
      }
      setSidebarRefreshKey((prev) => prev + 1);
    } catch (err) {
      showToast('Failed to modify accepted answer.', 'error');
    }
  }, [thread, showToast]);

  const loadMoreAnswers = useCallback(() => {
    setVisibleAnswersCount((prev) => prev + 10);
  }, []);

  const isThreadOwner = thread ? thread.authorId === userId : false;

  return {
    thread,
    loading,
    error,
    visibleAnswersCount,
    loadMoreAnswers,
    newAnswerBody,
    setNewAnswerBody,
    isSubmittingAnswer,
    handleAnswerSubmit,
    handleThreadUpvote,
    handleThreadDelete,
    handleToggleSolved,
    handleAnswerUpvote,
    handleAnswerDelete,
    editingAnswerId,
    editingAnswerBody,
    setEditingAnswerBody,
    isSavingAnswerEdit,
    startEditingAnswer,
    cancelEditingAnswer,
    handleAnswerEditSave,
    handleAcceptAnswer,
    isThreadOwner,
    sidebarRefreshKey,
  };
}
