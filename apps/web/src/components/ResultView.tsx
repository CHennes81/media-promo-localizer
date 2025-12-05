import type { LocalizationResult } from '../types/api';
import { SUPPORTED_LANGUAGES } from './LanguageSelector';
import './ResultView.css';

interface ResultViewProps {
  result: LocalizationResult;
  originalImageUrl: string;
}

export function ResultView({ result, originalImageUrl }: ResultViewProps) {
  const languageLabel =
    SUPPORTED_LANGUAGES.find((lang) => lang.code === result.language)?.label || result.language;

  const formatTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="result-view">
      <div className="result-header">
        <h3 className="result-title">Localization Complete</h3>
        <div className="result-language-badge">{languageLabel}</div>
      </div>

      <div className="result-comparison">
        <div className="result-image-container">
          <div className="result-image-label">Original</div>
          <img src={originalImageUrl} alt="Original poster" className="result-image" />
        </div>
        <div className="result-arrow">→</div>
        <div className="result-image-container">
          <div className="result-image-label">Localized</div>
          <img src={result.imageUrl} alt="Localized poster" className="result-image" />
        </div>
      </div>

      <div className="result-stats">
        <div className="result-stats-title">Processing Times</div>
        <div className="result-stats-grid">
          <div className="result-stat">
            <div className="result-stat-label">OCR</div>
            <div className="result-stat-value">{formatTime(result.processingTimeMs.ocr)}</div>
          </div>
          <div className="result-stat">
            <div className="result-stat-label">Translation</div>
            <div className="result-stat-value">
              {formatTime(result.processingTimeMs.translation)}
            </div>
          </div>
          <div className="result-stat">
            <div className="result-stat-label">Inpaint</div>
            <div className="result-stat-value">{formatTime(result.processingTimeMs.inpaint)}</div>
          </div>
          <div className="result-stat">
            <div className="result-stat-label">Packaging</div>
            <div className="result-stat-value">{formatTime(result.processingTimeMs.packaging)}</div>
          </div>
          <div className="result-stat result-stat-total">
            <div className="result-stat-label">Total</div>
            <div className="result-stat-value">{formatTime(result.processingTimeMs.total)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
