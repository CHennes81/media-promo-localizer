import { useState } from 'react';
import { buildInfo } from '../buildInfo';

export function AboutDialog() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        className="about-btn"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="about-dialog"
      >
        About
      </button>

      {open && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="about-title"
          id="about-dialog"
          onClick={() => setOpen(false)}
        >
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h2 id="about-title">About This Build</h2>
            <div style={{ lineHeight: 1.6 }}>
              <div>
                <strong>Version:</strong> {buildInfo.version}
              </div>
              <div>
                <strong>Commit:</strong> {buildInfo.commit}
              </div>
              <div>
                <strong>Built:</strong> {new Date(buildInfo.buildTime).toLocaleString()}
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => setOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
