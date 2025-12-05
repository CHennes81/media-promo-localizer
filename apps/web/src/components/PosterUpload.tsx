import { useRef, useState, type DragEvent, type ChangeEvent } from 'react';
import './PosterUpload.css';

interface PosterUploadProps {
  selectedFile: File | null;
  onFileSelect: (file: File) => void;
  onFileClear: () => void;
}

export function PosterUpload({ selectedFile, onFileSelect, onFileClear }: PosterUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a JPEG or PNG image file.');
      return false;
    }
    setError('');
    return true;
  };

  const handleFile = (file: File) => {
    if (validateFile(file)) {
      onFileSelect(file);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleClear = () => {
    onFileClear();
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (selectedFile) {
    const previewUrl = URL.createObjectURL(selectedFile);
    return (
      <div className="poster-upload">
        <div className="poster-preview-container">
          <img src={previewUrl} alt="Selected poster" className="poster-preview" />
          <button type="button" className="poster-clear-button" onClick={handleClear}>
            ×
          </button>
        </div>
        <p className="poster-filename">{selectedFile.name}</p>
      </div>
    );
  }

  return (
    <div className="poster-upload">
      <div
        className={`poster-dropzone ${isDragging ? 'dragging' : ''} ${error ? 'error' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/jpg,image/png"
          onChange={handleFileInputChange}
          className="poster-file-input"
          aria-label="Upload poster image"
        />
        <div className="poster-dropzone-content">
          <svg
            className="poster-upload-icon"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="poster-dropzone-text">
            Drag and drop your poster here, or{' '}
            <button type="button" className="poster-browse-link" onClick={handleBrowseClick}>
              browse
            </button>
          </p>
          <p className="poster-dropzone-hint">JPEG or PNG only</p>
        </div>
      </div>
      {error && <div className="poster-error">{error}</div>}
    </div>
  );
}
