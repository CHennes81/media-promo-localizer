/**
 * Localization API client that always calls the backend API.
 * No mock mode selection - frontend always uses this client.
 */

import type { CreateJobRequest, LocalizationJob } from '../types/api';
import { logger } from '../utils/logger';

/**
 * Get the API base URL from environment or default to localhost.
 */
function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
}

/**
 * LocalizationApiClient - always calls the backend API.
 */
export class LocalizationApiClient {
  private readonly apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = getApiBaseUrl();
    logger.info('LocalizationApiClient initialized', {
      component: 'LocalizationApiClient',
      action: 'init',
      apiBaseUrl: this.apiBaseUrl,
    });
  }

  /**
   * Create a new localization job.
   */
  async createJob(request: CreateJobRequest): Promise<LocalizationJob> {
    const startTime = Date.now();
    const url = `${this.apiBaseUrl}/v1/localization-jobs`;

    logger.info('Creating localization job', {
      component: 'LocalizationApiClient',
      action: 'createJob',
      url,
      targetLanguage: request.targetLanguage,
      fileName: request.file.name,
      fileSize: request.file.size,
    });

    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(request.file.type)) {
      throw new Error('Unsupported file type. Please use JPEG or PNG.');
    }

    // Prepare form data
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('targetLanguage', request.targetLanguage);
    if (request.sourceLanguage) {
      formData.append('sourceLanguage', request.sourceLanguage);
    }
    if (request.jobMetadata) {
      formData.append('jobMetadata', JSON.stringify(request.jobMetadata));
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      const requestDuration = Date.now() - startTime;

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorBody = await response.json();
          if (errorBody.error?.message) {
            errorMessage = errorBody.error.message;
          }
        } catch {
          // Ignore JSON parse errors, use default message
        }

        logger.error('Failed to create localization job', {
          component: 'LocalizationApiClient',
          action: 'createJobError',
          status: response.status,
          statusText: response.statusText,
          requestDurationMs: requestDuration,
        });

        throw new Error(errorMessage);
      }

      const job: LocalizationJob = await response.json();

      logger.info('Localization job created', {
        component: 'LocalizationApiClient',
        action: 'jobCreated',
        jobId: job.jobId,
        status: job.status,
        requestDurationMs: requestDuration,
      });

      return job;
    } catch (error) {
      const requestDuration = Date.now() - startTime;
      logger.error(
        'Exception creating localization job',
        {
          component: 'LocalizationApiClient',
          action: 'createJobException',
          requestDurationMs: requestDuration,
        },
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    }
  }

  /**
   * Get job status and result.
   */
  async getJob(jobId: string): Promise<LocalizationJob | null> {
    const startTime = Date.now();
    const url = `${this.apiBaseUrl}/v1/localization-jobs/${jobId}`;

    logger.debug('Getting localization job', {
      component: 'LocalizationApiClient',
      action: 'getJob',
      jobId,
      url,
    });

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const requestDuration = Date.now() - startTime;

      if (response.status === 404) {
        logger.warn('Job not found (404)', {
          component: 'LocalizationApiClient',
          action: 'Polling404',
          jobId,
          requestDurationMs: requestDuration,
        });
        return null;
      }

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorBody = await response.json();
          if (errorBody.error?.message) {
            errorMessage = errorBody.error.message;
          }
        } catch {
          // Ignore JSON parse errors
        }

        logger.error('Failed to get localization job', {
          component: 'LocalizationApiClient',
          action: 'getJobError',
          jobId,
          status: response.status,
          statusText: response.statusText,
          requestDurationMs: requestDuration,
        });

        throw new Error(errorMessage);
      }

      const job: LocalizationJob = await response.json();

      logger.debug('Retrieved localization job', {
        component: 'LocalizationApiClient',
        action: 'getJobSuccess',
        jobId,
        status: job.status,
        requestDurationMs: requestDuration,
      });

      return job;
    } catch (error) {
      const requestDuration = Date.now() - startTime;
      logger.error(
        'Exception getting localization job',
        {
          component: 'LocalizationApiClient',
          action: 'getJobException',
          jobId,
          requestDurationMs: requestDuration,
        },
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    }
  }

  /**
   * Subscribe to job updates by polling.
   * Returns an unsubscribe function.
   */
  subscribeToJob(
    jobId: string,
    onUpdate: (job: LocalizationJob) => void,
    intervalMs: number = 1000,
  ): () => void {
    let isActive = true;

    const poll = async () => {
      if (!isActive) return;

      try {
        const job = await this.getJob(jobId);
        if (job) {
          onUpdate(job);
          // Continue polling if job is still in progress
          if (job.status === 'queued' || job.status === 'processing') {
            setTimeout(poll, intervalMs);
          } else {
            // Job completed (succeeded or failed), stop polling
            isActive = false;
          }
        } else {
          // Job not found (404), stop polling and notify callback with null
          logger.warn('Job not found during polling, stopping', {
            component: 'LocalizationApiClient',
            action: 'subscribeToJobNotFound',
            jobId,
          });
          // Notify callback that job was not found
          onUpdate({
            jobId,
            status: 'failed',
            createdAt: new Date().toISOString(),
            error: {
              code: 'NOT_FOUND',
              message:
                'Job not found (possibly server restarted / store cleared). Please resubmit.',
              retryable: false,
            },
          } as LocalizationJob);
          isActive = false;
        }
      } catch (error) {
        logger.error(
          'Error polling job status',
          {
            component: 'LocalizationApiClient',
            action: 'subscribeToJobError',
            jobId,
          },
          error instanceof Error ? error : new Error(String(error)),
        );
        // Continue polling on error (might be transient)
        if (isActive) {
          setTimeout(poll, intervalMs);
        }
      }
    };

    // Start polling
    setTimeout(poll, intervalMs);

    // Return unsubscribe function
    return () => {
      isActive = false;
    };
  }

  /**
   * Cleanup method for compatibility (no-op for API client).
   * Object URLs are managed by the backend.
   */
  revokeJobUrls(_jobId: string): void {
    // No-op: backend manages URLs
  }
}

// Singleton instance
export const localizationApiClient = new LocalizationApiClient();
