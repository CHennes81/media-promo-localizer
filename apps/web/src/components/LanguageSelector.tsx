import './LanguageSelector.css';

export interface LanguageOption {
  code: string;
  label: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en-US', label: 'English (US)' },
  { code: 'es-MX', label: 'Spanish (Mexico)' },
  { code: 'fr-FR', label: 'French (France)' },
  { code: 'pt-BR', label: 'Portuguese (Brazil)' },
  { code: 'ja-JP', label: 'Japanese (Japan)' },
];

interface LanguageSelectorProps {
  selectedLanguage: string;
  onLanguageChange: (language: string) => void;
}

export function LanguageSelector({ selectedLanguage, onLanguageChange }: LanguageSelectorProps) {
  return (
    <div className="language-selector">
      <label className="language-selector-label">Target Language</label>
      <div className="language-selector-options">
        {SUPPORTED_LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            type="button"
            className={`language-option ${selectedLanguage === lang.code ? 'selected' : ''}`}
            onClick={() => onLanguageChange(lang.code)}
          >
            <span className="language-label">{lang.label}</span>
            <span className="language-code">{lang.code}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
