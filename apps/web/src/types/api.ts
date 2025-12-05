// Types matching the API contract from artifacts/API_Definition.md

export type JobStatus = 'queued' | 'processing' | 'succeeded' | 'failed' | 'canceled';

export type ProcessingStage = 'ocr' | 'translation' | 'inpaint' | 'packaging';

export interface StageTimingsMs {
  ocr: number;
  translation: number;
  inpaint: number;
  packaging: number;
}

export interface ProcessingTimeMs extends StageTimingsMs {
  total: number;
}

export interface JobProgress {
  stage: ProcessingStage;
  percent: number;
  stageTimingsMs: StageTimingsMs;
}

export interface DetectedText {
  text: string;
  boundingBox: [number, number, number, number];
  role: 'title' | 'tagline' | 'credits' | 'rating' | 'other';
}

export interface LocalizationResult {
  imageUrl: string;
  thumbnailUrl?: string;
  processingTimeMs: ProcessingTimeMs;
  language: string;
  sourceLanguage?: string;
  detectedText?: DetectedText[];
}

export interface JobError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface LocalizationJob {
  jobId: string;
  status: JobStatus;
  createdAt: string;
  updatedAt?: string;
  estimatedSeconds?: number;
  progress?: JobProgress;
  result?: LocalizationResult | null;
  error?: JobError | null;
}

export interface CreateJobRequest {
  file: File;
  targetLanguage: string;
  sourceLanguage?: string;
  jobMetadata?: Record<string, unknown>;
}
