// Mock localization service that simulates the async job API
// No real network calls - all in-memory simulation

import type {
  CreateJobRequest,
  LocalizationJob,
  ProcessingStage,
  StageTimingsMs,
  ProcessingTimeMs,
} from '../types/api';

// Simulated processing times (in milliseconds)
const STAGE_DURATIONS: Record<ProcessingStage, number> = {
  ocr: 1200,
  translation: 800,
  inpaint: 4300,
  packaging: 500,
};

const TOTAL_DURATION = Object.values(STAGE_DURATIONS).reduce((a, b) => a + b, 0);

// Generate a fake job ID
function generateJobId(): string {
  return `loc_${Date.now().toString(36).toUpperCase()}_${Math.random().toString(36).substring(2, 11)}`;
}

// Create a placeholder image URL (using a data URL or placeholder service)
function createPlaceholderImageUrl(originalFile: File): string {
  // For demo, we'll create a data URL from the original file
  // In a real app, this would be a CDN URL
  return URL.createObjectURL(originalFile);
}

// Simulate job progress updates
async function simulateJobProgress(
  jobId: string,
  targetLanguage: string,
  originalFile: File,
  onProgress: (job: LocalizationJob) => void,
): Promise<LocalizationJob> {
  const stages: ProcessingStage[] = ['ocr', 'translation', 'inpaint', 'packaging'];
  const startTime = Date.now();
  const stageTimings: StageTimingsMs = {
    ocr: 0,
    translation: 0,
    inpaint: 0,
    packaging: 0,
  };

  // Initial queued state
  let job: LocalizationJob = {
    jobId,
    status: 'queued',
    createdAt: new Date().toISOString(),
    estimatedSeconds: Math.ceil(TOTAL_DURATION / 1000),
  };
  onProgress(job);

  // Small delay before starting
  await new Promise((resolve) => setTimeout(resolve, 300));

  // Process through each stage
  for (let i = 0; i < stages.length; i++) {
    const stage = stages[i];
    const stageDuration = STAGE_DURATIONS[stage];
    const stageStartTime = Date.now();

    // Update to processing status
    job = {
      ...job,
      status: 'processing',
      updatedAt: new Date().toISOString(),
      progress: {
        stage,
        percent: Math.round(((i + 0.1) / stages.length) * 100),
        stageTimingsMs: { ...stageTimings },
      },
    };
    onProgress(job);

    // Simulate stage progress with intermediate updates
    const progressSteps = 3;
    for (let step = 1; step <= progressSteps; step++) {
      await new Promise((resolve) => setTimeout(resolve, stageDuration / progressSteps));
      const elapsed = Date.now() - stageStartTime;
      stageTimings[stage] = elapsed;

      job = {
        ...job,
        updatedAt: new Date().toISOString(),
        progress: {
          stage,
          percent: Math.round(((i + step / progressSteps) / stages.length) * 100),
          stageTimingsMs: { ...stageTimings },
        },
      };
      onProgress(job);
    }
  }

  // Finalize with succeeded status
  const totalTime = Date.now() - startTime;
  const processingTimeMs: ProcessingTimeMs = {
    ...stageTimings,
    total: totalTime,
  };

  job = {
    ...job,
    status: 'succeeded',
    updatedAt: new Date().toISOString(),
    progress: {
      stage: 'packaging',
      percent: 100,
      stageTimingsMs: stageTimings,
    },
    result: {
      imageUrl: createPlaceholderImageUrl(originalFile),
      thumbnailUrl: createPlaceholderImageUrl(originalFile),
      processingTimeMs,
      language: targetLanguage,
      sourceLanguage: 'en-US',
      detectedText: [
        {
          text: 'THE GREAT HEIST',
          boundingBox: [100, 200, 800, 280],
          role: 'title',
        },
        {
          text: 'COMING SOON',
          boundingBox: [120, 900, 780, 950],
          role: 'tagline',
        },
      ],
    },
  };

  onProgress(job);
  return job;
}

export class MockLocalizationService {
  private activeJobs = new Map<string, LocalizationJob>();

  async createJob(request: CreateJobRequest): Promise<LocalizationJob> {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(request.file.type)) {
      throw new Error('Unsupported file type. Please use JPEG or PNG.');
    }

    const jobId = generateJobId();
    const job: LocalizationJob = {
      jobId,
      status: 'queued',
      createdAt: new Date().toISOString(),
      estimatedSeconds: Math.ceil(TOTAL_DURATION / 1000),
    };

    this.activeJobs.set(jobId, job);

    // Start simulation asynchronously
    simulateJobProgress(jobId, request.targetLanguage, request.file, (updatedJob) => {
      this.activeJobs.set(jobId, updatedJob);
    }).catch((error) => {
      // Handle simulation errors
      const failedJob: LocalizationJob = {
        ...job,
        status: 'failed',
        updatedAt: new Date().toISOString(),
        error: {
          code: 'INTERNAL_ERROR',
          message: error.message || 'Job simulation failed',
          retryable: true,
        },
      };
      this.activeJobs.set(jobId, failedJob);
    });

    return job;
  }

  async getJob(jobId: string): Promise<LocalizationJob | null> {
    return this.activeJobs.get(jobId) || null;
  }

  // Polling helper for UI
  subscribeToJob(
    jobId: string,
    onUpdate: (job: LocalizationJob) => void,
    intervalMs: number = 500,
  ): () => void {
    const intervalId = setInterval(() => {
      const job = this.activeJobs.get(jobId);
      if (job) {
        onUpdate(job);
        if (job.status === 'succeeded' || job.status === 'failed') {
          clearInterval(intervalId);
        }
      }
    }, intervalMs);

    // Return unsubscribe function
    return () => clearInterval(intervalId);
  }
}

// Singleton instance
export const mockLocalizationService = new MockLocalizationService();
