import { useState, useEffect } from 'react';
import { PosterUpload } from './PosterUpload';
import { LanguageSelector, SUPPORTED_LANGUAGES } from './LanguageSelector';
import { ProcessingAnimation } from './ProcessingAnimation';
import { ResultView } from './ResultView';
import { mockLocalizationService } from '../services/mockLocalizationService';
import type { LocalizationJob } from '../types/api';
import { useAuth } from '../contexts/AuthContext';
import './LocalizationWorkspace.css';

export function LocalizationWorkspace() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState(SUPPORTED_LANGUAGES[0].code);
  const [currentJob, setCurrentJob] = useState<LocalizationJob | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string>('');
  const { logout } = useAuth();

  useEffect(() => {
    // Cleanup object URLs on unmount
    return () => {
      if (originalImageUrl && originalImageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(originalImageUrl);
      }
    };
  }, [originalImageUrl]);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setCurrentJob(null);
    // Create object URL for preview
    if (originalImageUrl && originalImageUrl.startsWith('blob:')) {
      URL.revokeObjectURL(originalImageUrl);
    }
    setOriginalImageUrl(URL.createObjectURL(file));
  };

  const handleFileClear = () => {
    setSelectedFile(null);
    setCurrentJob(null);
    if (originalImageUrl && originalImageUrl.startsWith('blob:')) {
      URL.revokeObjectURL(originalImageUrl);
    }
    setOriginalImageUrl('');
  };

  const handleLocalize = async () => {
    if (!selectedFile) return;

    try {
      const job = await mockLocalizationService.createJob({
        file: selectedFile,
        targetLanguage: selectedLanguage,
      });

      setCurrentJob(job);

      // Subscribe to job updates
      const unsubscribe = mockLocalizationService.subscribeToJob(job.jobId, (updatedJob) => {
        setCurrentJob(updatedJob);
      });

      // Cleanup subscription when job completes
      if (job.status === 'succeeded' || job.status === 'failed') {
        unsubscribe();
      } else {
        // Auto-unsubscribe after a delay (job will complete via simulation)
        setTimeout(() => {
          unsubscribe();
        }, 10000);
      }
    } catch (error) {
      console.error('Failed to create localization job:', error);
      // TODO: Show error message to user
    }
  };

  const canLocalize = selectedFile !== null && selectedLanguage !== '';
  const isProcessing = currentJob?.status === 'queued' || currentJob?.status === 'processing';
  const isComplete = currentJob?.status === 'succeeded';
  const hasError = currentJob?.status === 'failed';

  return (
    <div className="workspace">
      <header className="workspace-header">
        <div className="workspace-header-content">
          <h1 className="workspace-title">Media Promo Localizer</h1>
          <button type="button" className="workspace-logout-button" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <main className="workspace-main">
        <div className="workspace-grid">
          <section className="workspace-section workspace-section-upload">
            <h2 className="workspace-section-title">Upload Poster</h2>
            <PosterUpload
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              onFileClear={handleFileClear}
            />
          </section>

          <section className="workspace-section workspace-section-language">
            <h2 className="workspace-section-title">Target Language</h2>
            <LanguageSelector
              selectedLanguage={selectedLanguage}
              onLanguageChange={setSelectedLanguage}
            />
          </section>

          <section className="workspace-section workspace-section-actions">
            <button
              type="button"
              className="workspace-localize-button"
              onClick={handleLocalize}
              disabled={!canLocalize || isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Localize Poster'}
            </button>
          </section>

          {isProcessing && currentJob?.progress && (
            <section className="workspace-section workspace-section-processing">
              <ProcessingAnimation
                stage={currentJob.progress.stage}
                percent={currentJob.progress.percent}
                stageTimingsMs={currentJob.progress.stageTimingsMs}
              />
            </section>
          )}

          {hasError && currentJob?.error && (
            <section className="workspace-section workspace-section-error">
              <div className="workspace-error">
                <h3>Localization Failed</h3>
                <p>{currentJob.error.message}</p>
                {currentJob.error.retryable && (
                  <button type="button" className="workspace-retry-button" onClick={handleLocalize}>
                    Retry
                  </button>
                )}
              </div>
            </section>
          )}

          {isComplete && currentJob?.result && originalImageUrl && (
            <section className="workspace-section workspace-section-result">
              <ResultView result={currentJob.result} originalImageUrl={originalImageUrl} />
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
