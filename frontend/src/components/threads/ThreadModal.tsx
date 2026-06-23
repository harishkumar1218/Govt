import React, { useState, useEffect, useRef } from 'react';
import styles from './Threads.module.css';

interface ThreadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, body: string, category: string) => Promise<void>;
  initialTitle?: string;
  initialBody?: string;
  initialCategory?: string;
  isEditMode?: boolean;
}

export default function ThreadModal({
  isOpen,
  onClose,
  onSubmit,
  initialTitle = '',
  initialBody = '',
  initialCategory = 'General',
  isEditMode = false,
}: ThreadModalProps) {
  const [title, setTitle] = useState(initialTitle);
  const [body, setBody] = useState(initialBody);
  const [category, setCategory] = useState(initialCategory);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Validation errors near fields
  const [titleError, setTitleError] = useState<string | null>(null);
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const titleInputRef = useRef<HTMLInputElement>(null);

  const categories = ['Polity', 'Economy', 'History', 'Geography', 'Current Affairs', 'Essay', 'CSAT', 'General'];

  useEffect(() => {
    if (isOpen) {
      setTitle(initialTitle);
      setBody(initialBody);
      setCategory(initialCategory);
      setTitleError(null);
      setBodyError(null);
      setGeneralError(null);
      
      // Autofocus
      setTimeout(() => {
        titleInputRef.current?.focus();
      }, 50);
    }
  }, [isOpen, initialTitle, initialBody, initialCategory]);

  // Click outside / escape confirmation handler
  const handleCloseRequest = () => {
    const hasUnsavedChanges = 
      title.trim() !== initialTitle.trim() || 
      body.trim() !== initialBody.trim() || 
      category !== initialCategory;

    if (!hasUnsavedChanges || window.confirm('Discard your unsaved doubt details?')) {
      onClose();
    }
  };

  // Keyboard listener for Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleCloseRequest();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, title, body, category]);

  if (!isOpen) return null;

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTitleError(null);
    setBodyError(null);
    setGeneralError(null);

    const trimmedTitle = title.trim();
    const trimmedBody = body.trim();
    let hasError = false;

    if (!trimmedTitle) {
      setTitleError('Title is required.');
      hasError = true;
    } else if (trimmedTitle.length > 120) {
      setTitleError('Title cannot exceed 120 characters.');
      hasError = true;
    }

    if (!trimmedBody) {
      setBodyError('Doubt description is required.');
      hasError = true;
    } else if (trimmedBody.length > 2000) {
      setBodyError('Description cannot exceed 2000 characters.');
      hasError = true;
    }

    if (hasError) return;

    setIsSubmitting(true);
    try {
      await onSubmit(trimmedTitle, trimmedBody, category);
      onClose();
    } catch (err: any) {
      setGeneralError(err.message || 'An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={handleCloseRequest}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className={styles.modalHeader}>
          <h2 id="modal-title">{isEditMode ? 'Edit Doubt' : 'Ask a Doubt'}</h2>
          <button 
            className={styles.closeBtn} 
            onClick={handleCloseRequest} 
            aria-label="Close composer modal"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {generalError && (
          <div className={styles.errorState} style={{ marginBottom: '0.5rem', fontWeight: 'bold' }}>
            ⚠️ {generalError}
          </div>
        )}

        <form onSubmit={handleFormSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label htmlFor="thread-title">Title</label>
            <input
              id="thread-title"
              ref={titleInputRef}
              type="text"
              className={styles.modalInput}
              placeholder="What is your doubt or concept question?"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (titleError) setTitleError(null);
              }}
              disabled={isSubmitting}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span className={styles.validationError}>{titleError}</span>
              <span className={styles.charCount}>{title.length}/120</span>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="thread-category">Subject Category</label>
            <select
              id="thread-category"
              className={styles.modalInput}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isSubmitting}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="thread-body">Description</label>
            <textarea
              id="thread-body"
              className={styles.modalTextarea}
              placeholder="Explain your doubt in detail. Provide any paper reference, book context, or specific parts you find confusing..."
              value={body}
              onChange={(e) => {
                setBody(e.target.value);
                if (bodyError) setBodyError(null);
              }}
              disabled={isSubmitting}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span className={styles.validationError}>{bodyError}</span>
              <span className={styles.charCount}>{body.length}/2000</span>
            </div>
          </div>

          <div className={styles.modalActions}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCloseRequest}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Posting...' : isEditMode ? 'Save Changes' : 'Post Doubt'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
