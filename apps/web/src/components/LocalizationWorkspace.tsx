import { useState, useEffect, useRef } from 'react';
import { PosterUpload } from './PosterUpload';
import { LanguageSelector, SUPPORTED_LANGUAGES } from './LanguageSelector';
import { ProcessingAnimation } from './ProcessingAnimation';
import { ResultView } from './ResultView';
import { localizationApiClient } from '../services/localizationApiClient';
import type { LocalizationJob } from '../types/api';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../utils/logger';
import './LocalizationWorkspace.css';

export function LocalizationWorkspace() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState(SUPPORTED_LANGUAGES[0].code);
  const [currentJob, setCurrentJob] = useState<LocalizationJob | null>(null);
  const [originalImageUrl, setOriginalImageUrl] = useState<string>('');
  const previousJobIdRef = useRef<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { logout } = useAuth();

  // Cleanup originalImageUrl when it changes
  useEffect(() => {
    return () => {
      if (originalImageUrl && originalImageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(originalImageUrl);
      }
    };
  }, [originalImageUrl]);

  // Cleanup job result URLs only when switching to a different job or unmounting
  useEffect(() => {
    const currentJobId = currentJob?.jobId ?? null;

    // If we're switching from one job to another (or clearing), cleanup previous job
    if (previousJobIdRef.current !== null && previousJobIdRef.current !== currentJobId) {
      localizationApiClient.revokeJobUrls(previousJobIdRef.current);
    }

    previousJobIdRef.current = currentJobId;

    // Cleanup on unmount
    return () => {
      if (previousJobIdRef.current !== null) {
        localizationApiClient.revokeJobUrls(previousJobIdRef.current);
      }
    };
  }, [currentJob?.jobId]);

  // Cleanup subscriptions and timeouts on unmount
  useEffect(() => {
    return () => {
      // Clear any pending timeout
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      // Unsubscribe from any active subscription
      if (unsubscribeRef.current !== null) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    };
  }, []);

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

    const startTime = Date.now();

    logger.info('LocalizePoster clicked', {
      component: 'LocalizationWorkspace',
      action: 'localize',
      targetLanguage: selectedLanguage,
      fileName: selectedFile.name,
      fileSize: selectedFile.size,
    });

    // Clean up any previous subscription and timeout before starting a new job
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (unsubscribeRef.current !== null) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    try {
      logger.info('Creating localization job', {
        component: 'LocalizationWorkspace',
        action: 'createJob',
        method: 'POST',
      });

      const job = await localizationApiClient.createJob({
        file: selectedFile,
        targetLanguage: selectedLanguage,
      });

      const requestDuration = Date.now() - startTime;

      // CRITICAL: Always use jobId from create response, never a cached/stale value
      const createdJobId = job.jobId;

      logger.info('Localization job created', {
        component: 'LocalizationWorkspace',
        action: 'jobCreated',
        jobId: createdJobId,
        status: job.status,
        requestDurationMs: requestDuration,
      });

      // Clear any previous job state before setting new job
      setCurrentJob(null);
      setCurrentJob(job);

      // Subscribe to job updates using the jobId from create response
      logger.info('Starting job polling', {
        component: 'LocalizationWorkspace',
        action: 'startPolling',
        jobId: createdJobId,
      });

      const unsubscribe = localizationApiClient.subscribeToJob(createdJobId, (updatedJob) => {
        // Verify we're still tracking the same jobId
        if (updatedJob.jobId !== createdJobId) {
          logger.error('JobId mismatch during polling', {
            component: 'LocalizationWorkspace',
            action: 'jobIdMismatch',
            expectedJobId: createdJobId,
            receivedJobId: updatedJob.jobId,
          });
          return;
        }

        setCurrentJob(updatedJob);
        setCurrentJob(updatedJob);
        // If job completes, clean up immediately
        if (updatedJob.status === 'succeeded' || updatedJob.status === 'failed') {
          if (timeoutRef.current !== null) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
          if (unsubscribeRef.current !== null) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
          }
        }
      });

      // Store unsubscribe function for cleanup
      unsubscribeRef.current = unsubscribe;

      // Cleanup subscription when job completes
      if (job.status === 'succeeded' || job.status === 'failed') {
        unsubscribe();
        unsubscribeRef.current = null;
      } else {
        // Auto-unsubscribe after a delay (safety timeout)
        timeoutRef.current = setTimeout(() => {
          if (unsubscribeRef.current !== null) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
          }
          timeoutRef.current = null;
        }, 60000); // 60 second timeout for safety
      }
    } catch (error) {
      const requestDuration = Date.now() - startTime;
      logger.error(
        'Failed to create localization job',
        {
          component: 'LocalizationWorkspace',
          action: 'createJobError',
          requestDurationMs: requestDuration,
        },
        error instanceof Error ? error : new Error(String(error)),
      );
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
          <div className="workspace-logo">
            <svg
              className="workspace-logo-icon"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 9h6v6H9z" />
              <path d="M3 12h18" />
              <path d="M12 3v18" />
            </svg>
            <h1 className="workspace-title">Media Promo Localizer</h1>
          </div>
          <button type="button" className="workspace-logout-button" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <main className="workspace-main">
        <div className="workspace-background">
          <div className="workspace-gradient-orb workspace-gradient-orb-1" />
          <div className="workspace-gradient-orb workspace-gradient-orb-2" />
          <div className="workspace-gradient-orb workspace-gradient-orb-3" />
        </div>
        <div className="workspace-content">
          <div className="workspace-stack">
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
          </div>

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
                {currentJob.error.code === 'NOT_FOUND' && (
                  <p className="workspace-error-hint">
                    The job may have been lost due to a server restart. Please upload and localize
                    again.
                  </p>
                )}
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
