import { useState, useRef, useEffect } from 'react';
import type { LocalizationResult, DebugTextRegion } from '../types/api';
import { SUPPORTED_LANGUAGES } from './LanguageSelector';
import './ResultView.css';

interface ResultViewProps {
  result: LocalizationResult;
  originalImageUrl: string;
}

export function ResultView({ result, originalImageUrl }: ResultViewProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [showOcrBoxes, setShowOcrBoxes] = useState(false);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(
    null,
  );
  const imageRef = useRef<HTMLImageElement>(null);

  const languageLabel =
    SUPPORTED_LANGUAGES.find((lang) => lang.code === result.language)?.label || result.language;

  const formatTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Track image dimensions for overlay positioning
  useEffect(() => {
    const img = imageRef.current;
    if (img) {
      const updateDimensions = () => {
        setImageDimensions({ width: img.offsetWidth, height: img.offsetHeight });
      };
      img.addEventListener('load', updateDimensions);
      updateDimensions();
      return () => img.removeEventListener('load', updateDimensions);
    }
  }, [result.imageUrl]);

  const debugRegions = result.debug?.regions || [];

  return (
    <div className="result-view">
      <div className="result-header">
        <h3 className="result-title">Localization Complete</h3>
        <div className="result-language-badge">{languageLabel}</div>
      </div>

      <div className="result-image-wrapper">
        <div className="result-image-container-single">
          <img
            src={result.imageUrl}
            alt="Localized poster"
            className="result-image-large"
            ref={imageRef}
          />
          {showOcrBoxes && imageDimensions && debugRegions.length > 0 && (
            <div className="result-ocr-overlays">
              {debugRegions.map((region) => {
                const [x, y, width, height] = region.bbox_norm;
                const left = x * imageDimensions.width;
                const top = y * imageDimensions.height;
                const boxWidth = width * imageDimensions.width;
                const boxHeight = height * imageDimensions.height;

                return (
                  <div
                    key={region.id}
                    className="result-ocr-box"
                    style={{
                      left: `${left}px`,
                      top: `${top}px`,
                      width: `${boxWidth}px`,
                      height: `${boxHeight}px`,
                    }}
                    title={`${region.role}: ${region.original_text}`}
                  />
                );
              })}
            </div>
          )}
        </div>
        <div className="result-controls">
          <button
            type="button"
            className="result-button"
            onClick={() => setShowDetails(true)}
            disabled={!result.debug || debugRegions.length === 0}
          >
            View Details
          </button>
          <label className="result-toggle">
            <input
              type="checkbox"
              checked={showOcrBoxes}
              onChange={(e) => setShowOcrBoxes(e.target.checked)}
              disabled={!result.debug || debugRegions.length === 0}
            />
            <span>Show OCR Boxes</span>
          </label>
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

      {showDetails && (
        <DetailsDialog regions={debugRegions} onClose={() => setShowDetails(false)} />
      )}
    </div>
  );
}

interface DetailsDialogProps {
  regions: DebugTextRegion[];
  onClose: () => void;
}

function DetailsDialog({ regions, onClose }: DetailsDialogProps) {
  if (regions.length === 0) {
    return (
      <div className="result-dialog-overlay" onClick={onClose}>
        <div className="result-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="result-dialog-header">
            <h3>Details</h3>
            <button type="button" className="result-dialog-close" onClick={onClose}>
              ×
            </button>
          </div>
          <div className="result-dialog-content">
            <p>No debug data available for this job.</p>
          </div>
        </div>
      </div>
    );
  }

  const formatBbox = (bbox: [number, number, number, number]): string => {
    const [x, y, w, h] = bbox;
    return `(${x.toFixed(3)}, ${y.toFixed(3)}, ${w.toFixed(3)}, ${h.toFixed(3)})`;
  };

  return (
    <div className="result-dialog-overlay" onClick={onClose}>
      <div className="result-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="result-dialog-header">
          <h3>Debug Details</h3>
          <button type="button" className="result-dialog-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="result-dialog-content">
          <div className="result-dialog-table-wrapper">
            <table className="result-dialog-table">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>BBox</th>
                  <th>Original Text</th>
                  <th>Translated Text</th>
                  <th>Localizable</th>
                </tr>
              </thead>
              <tbody>
                {regions.map((region) => (
                  <tr key={region.id}>
                    <td>{region.role}</td>
                    <td className="result-dialog-bbox">{formatBbox(region.bbox_norm)}</td>
                    <td className="result-dialog-text">{region.original_text}</td>
                    <td className="result-dialog-text">{region.translated_text || '—'}</td>
                    <td>{region.is_localizable ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
