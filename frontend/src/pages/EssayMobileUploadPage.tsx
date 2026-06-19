import React, { useState, useEffect } from 'react';
import { apiUrl } from '../config/api';
import styles from './EssayMobileUploadPage.module.css';

interface Props {
  token: string;
}

export default function EssayMobileUploadPage({ token }: Props) {
  const [question, setQuestion] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);

  useEffect(() => {
    fetchQuestionInfo();
  }, [token]);

  const fetchQuestionInfo = async () => {
    try {
      const res = await fetch(apiUrl(`/api/essay/upload/${token}/`));
      if (res.ok) {
        const data = await res.json();
        setQuestion(data);
      } else {
        const errData = await res.json();
        setError(errData.error || 'Failed to load question details.');
      }
    } catch (err) {
      setError('Network error. Please ensure you are connected to the same network as the server.');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setFiles(selectedFiles);

      // Generate previews
      const newPreviews = selectedFiles.map(file => URL.createObjectURL(file));
      setPreviews(newPreviews);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('images', file);
    });

    try {
      const res = await fetch(apiUrl(`/api/essay/upload/${token}/submit/`), {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setSuccess(true);
        setUploadedCount(data.uploaded_count);
      } else {
        const errData = await res.json();
        alert(`Upload failed: ${errData.error || 'Unknown error'}`);
      }
    } catch (err) {
      alert('Upload failed due to a network error.');
    } finally {
      setUploading(false);
    }
  };

  if (error) {
    return (
      <div className={styles.mobileWrapper}>
        <div className={styles.card} style={{ textAlign: 'center', marginTop: '2rem' }}>
          <h2 style={{ color: 'var(--danger)' }}>Error</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!question) {
    return <div className={styles.mobileWrapper} style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
  }

  if (success) {
    return (
      <div className={styles.mobileWrapper}>
        <div className={styles.successState}>
          <div className={styles.successIcon}>✅</div>
          <div className={styles.successTitle}>Upload Successful</div>
          <p>You have uploaded {uploadedCount} page(s) for Question {question.order}.</p>
          <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>You can close this tab and return to your desktop to <strong>Analyze Answer</strong> or submit the session.</p>
          
          <button className={styles.btnSecondary} onClick={() => {
            setSuccess(false);
            setFiles([]);
            setPreviews([]);
          }}>
            Upload more pages for this question
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.mobileWrapper}>
      <header className={styles.mobileHeader}>
        <div className={styles.mobileLogo}>UPSC Aspire Upload</div>
        <div className={styles.mobileSessionInfo}>{question.session_title}</div>
      </header>

      <div className={styles.card}>
        <div className={styles.qHeader}>
          <span>Question {question.order}</span>
          <span>{question.max_marks} Marks</span>
        </div>
        <div className={styles.qPrompt}>{question.prompt_text}</div>

        <div className={styles.uploadArea}>
          <label className={styles.uploadLabel}>Take photos of your answer sheet:</label>
          <input 
            type="file" 
            accept="image/*" 
            capture="environment" 
            multiple 
            onChange={handleFileChange}
            className={styles.fileInput}
          />

          {previews.length > 0 && (
            <div className={styles.previewGrid}>
              {previews.map((src, idx) => (
                <img key={idx} src={src} className={styles.previewImage} alt={`Preview ${idx + 1}`} />
              ))}
            </div>
          )}

          <button 
            className={styles.btnPrimary} 
            onClick={handleUpload} 
            disabled={uploading || files.length === 0}
          >
            {uploading ? 'Uploading...' : `Upload ${files.length} Page(s)`}
          </button>
        </div>
      </div>
    </div>
  );
}
