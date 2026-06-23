import React, { useState, useEffect, useRef } from 'react';
import { useThreadComposer } from './useThreadComposer';
import styles from './Threads.module.css';

interface ThreadComposerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, body: string, category: string, tags: string[]) => Promise<void>;
  initialTitle?: string;
  initialBody?: string;
  initialCategory?: string;
  initialTags?: string[];
  isEditMode?: boolean;
}

export default function ThreadComposerModal({
  isOpen,
  onClose,
  onSubmit,
  initialTitle = '',
  initialBody = '',
  initialCategory = 'General',
  initialTags = [],
  isEditMode = false,
}: ThreadComposerModalProps) {
  const composer = useThreadComposer({
    initialTitle,
    initialBody,
    initialCategory,
    initialTags,
    onSubmit,
  });

  const [activeTab, setActiveTab] = useState<'write' | 'preview'>('write');
  const titleInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      setActiveTab('write');
      composer.reset();
      setTimeout(() => {
        titleInputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Click outside / escape confirmation
  const handleCloseRequest = () => {
    if (!composer.isDirty() || window.confirm('Discard your unsaved doubt details?')) {
      onClose();
    }
  };

  // Keyboard Escape listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleCloseRequest();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, composer.title, composer.body, composer.category, composer.tagsInput]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await composer.submit();
    if (success) {
      onClose();
    }
  };

  // Safe preview renderer
  const renderPreview = () => {
    if (!composer.body.trim()) {
      return <p style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>Nothing to preview yet.</p>;
    }
    return composer.body.split('\n').map((para, i) => {
      if (!para.trim()) return <br key={i} />;
      if (para.trim().startsWith('- ') || para.trim().startsWith('* ')) {
        return (
          <li key={i} style={{ marginLeft: '1rem', listStyleType: 'disc', color: 'var(--text-color)' }}>
            {para.trim().slice(2)}
          </li>
        );
      }
      return <p key={i} style={{ marginBottom: '0.5rem', color: 'var(--text-color)' }}>{para}</p>;
    });
  };

  const categories = [
    'Polity', 'Economy', 'History', 'Geography', 
    'Current Affairs', 'Essay', 'CSAT', 'Ethics', 'Optional', 'General'
  ];

  return (
    <div className={styles.modalOverlay} onClick={handleCloseRequest}>
      <div 
        ref={modalRef}
        className={styles.modalContent} 
        onClick={(e) => e.stopPropagation()} 
        role="dialog" 
        aria-modal="true" 
        aria-labelledby="modal-title"
      >
        <div className={styles.modalHeader}>
          <h2 id="modal-title">{isEditMode ? 'Edit Doubt' : 'Ask a Doubt'}</h2>
          <button 
            className={styles.closeBtn} 
            onClick={handleCloseRequest} 
            aria-label="Close composer modal"
          >
            &times;
          </button>
        </div>

        {composer.generalError && (
          <div className={styles.errorState} style={{ marginBottom: '0.5rem', color: 'var(--text-danger)', fontWeight: 'bold' }}>
            ⚠️ {composer.generalError}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label htmlFor="thread-title">Title</label>
            <input
              id="thread-title"
              ref={titleInputRef}
              type="text"
              className={styles.modalInput}
              placeholder="What is your doubt or concept question? (min 8 chars)"
              value={composer.title}
              onChange={(e) => {
                composer.setTitle(e.target.value);
              }}
              disabled={composer.isSubmitting}
              aria-describedby="title-desc"
              required
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span id="title-desc" className={styles.validationError}>{composer.titleError}</span>
              <span className={styles.charCount}>{composer.title.length}/120</span>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="thread-category">Subject Category</label>
            <select
              id="thread-category"
              className={styles.modalInput}
              value={composer.category}
              onChange={(e) => composer.setCategory(e.target.value)}
              disabled={composer.isSubmitting}
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="thread-tags">Tags (comma-separated, max 5 tags)</label>
            <input
              id="thread-tags"
              type="text"
              className={styles.modalInput}
              placeholder="e.g. GS2, Article21, Laxmikanth"
              value={composer.tagsInput}
              onChange={(e) => {
                composer.setTagsInput(e.target.value);
              }}
              disabled={composer.isSubmitting}
              aria-describedby="tags-desc"
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span id="tags-desc" className={styles.validationError}>{composer.tagsError}</span>
            </div>
          </div>

          <div className={styles.formGroup}>
            <div className={styles.tabHeader}>
              <label htmlFor="thread-body" style={{ margin: 0 }}>Description</label>
              <div className={styles.tabButtons}>
                <button
                  type="button"
                  className={`${styles.modalTabBtn} ${activeTab === 'write' ? styles.modalActiveTabBtn : ''}`}
                  onClick={() => setActiveTab('write')}
                >
                  Write
                </button>
                <button
                  type="button"
                  className={`${styles.modalTabBtn} ${activeTab === 'preview' ? styles.modalActiveTabBtn : ''}`}
                  onClick={() => setActiveTab('preview')}
                >
                  Preview
                </button>
              </div>
            </div>

            {activeTab === 'write' ? (
              <textarea
                id="thread-body"
                className={styles.modalTextarea}
                placeholder="Explain your doubt in detail... (min 20 chars)"
                value={composer.body}
                onChange={(e) => {
                  composer.setBody(e.target.value);
                }}
                disabled={composer.isSubmitting}
                aria-describedby="body-desc"
                required
              />
            ) : (
              <div className={styles.previewContainer}>
                {renderPreview()}
              </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span id="body-desc" className={styles.validationError}>{composer.bodyError}</span>
              <span className={styles.charCount}>{composer.body.length}/3000</span>
            </div>
          </div>

          <div className={styles.modalActions}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleCloseRequest}
              disabled={composer.isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={composer.isSubmitting}
            >
              {composer.isSubmitting ? 'Posting...' : isEditMode ? 'Save Changes' : 'Post Doubt'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
