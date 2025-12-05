import { useState, type FormEvent } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginScreen.css';

export function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (login(email, password)) {
      // Success - auth context will update and trigger re-render
    } else {
      setError('Please enter both email and password');
    }
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-gradient-orb login-gradient-orb-1" />
        <div className="login-gradient-orb login-gradient-orb-2" />
        <div className="login-gradient-orb login-gradient-orb-3" />
      </div>
      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">Media Promo Localizer</h1>
          <p className="login-subtitle">Studio Portal</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="studio@example.com"
              autoComplete="email"
              required
            />
          </div>
          <div className="login-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-button">
            Enter Studio
          </button>
        </form>
      </div>
    </div>
  );
}
