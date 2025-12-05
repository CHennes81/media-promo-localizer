import type { ProcessingStage } from '../types/api';
import './ProcessingAnimation.css';

interface ProcessingAnimationProps {
  stage: ProcessingStage;
  percent: number;
  stageTimingsMs: Record<ProcessingStage, number>;
}

const STAGE_LABELS: Record<ProcessingStage, string> = {
  ocr: 'Extracting Text',
  translation: 'Translating',
  inpaint: 'Inpainting',
  packaging: 'Packaging',
};

export function ProcessingAnimation({ stage, percent, stageTimingsMs }: ProcessingAnimationProps) {
  const formatTime = (ms: number): string => {
    if (ms === 0) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const stages: ProcessingStage[] = ['ocr', 'translation', 'inpaint', 'packaging'];
  const currentStageIndex = stages.indexOf(stage);

  return (
    <div className="processing-container">
      <div className="processing-header">
        <h3 className="processing-title">Processing Localization</h3>
        <div className="processing-percent">{percent}%</div>
      </div>

      <div className="processing-progress-bar">
        <div className="processing-progress-fill" style={{ width: `${percent}%` }} />
      </div>

      <div className="processing-stages">
        {stages.map((s, index) => {
          const isActive = index === currentStageIndex;
          const isComplete = index < currentStageIndex;
          const timing = stageTimingsMs[s];

          return (
            <div
              key={s}
              className={`processing-stage ${isActive ? 'active' : ''} ${isComplete ? 'complete' : ''}`}
            >
              <div className="processing-stage-indicator">
                {isComplete ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="6" fill="#10b981" />
                    <path
                      d="M5 8l2 2 4-4"
                      stroke="#ffffff"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : isActive ? (
                  <div className="processing-spinner" />
                ) : (
                  <div className="processing-dot" />
                )}
              </div>
              <div className="processing-stage-content">
                <div className="processing-stage-label">{STAGE_LABELS[s]}</div>
                <div className="processing-stage-time">{formatTime(timing)}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
