import React, { useRef, useEffect } from 'react';
import styles from './Threads.module.css';

interface AnswerComposerProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isSubmitting: boolean;
}

export default function AnswerComposer({
  value,
  onChange,
  onSubmit,
  isSubmitting,
}: AnswerComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${ta.scrollHeight}px`;
    }
  }, [value]);

  // Keypress listener for Ctrl+Enter / Cmd+Enter
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      const length = value.trim().length;
      if (length >= 10 && length <= 2000 && !isSubmitting) {
        onSubmit(e);
      }
    }
  };

  const length = value.trim().length;
  const isValid = length >= 10 && length <= 2000;

  return (
    <form onSubmit={onSubmit} className={styles.answerComposer}>
      <div className={styles.formGroup} style={{ width: '100%' }}>
        <label htmlFor="answer-input" style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem', display: 'block' }}>
          Answer this doubt
        </label>
        <textarea
          id="answer-input"
          ref={textareaRef}
          className={styles.answerTextarea}
          placeholder="Write your answer... (min 10, max 2000 characters. Ctrl+Enter to submit)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSubmitting}
          aria-describedby="answer-char-count"
          required
        />
      </div>
      <div className={styles.composerActions}>
        <span id="answer-char-count" className={`${styles.charCount} ${value.length > 2000 ? styles.charCountError : ''}`} style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {value.length}/2000
        </span>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isSubmitting || !isValid}
        >
          {isSubmitting ? 'Posting...' : 'Post Answer'}
        </button>
      </div>
    </form>
  );
}
