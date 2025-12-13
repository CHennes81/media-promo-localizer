/**
 * Frontend logging utility for structured logging.
 * Logs to browser console with structured format.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  component?: string;
  action?: string;
  requestId?: string;
  jobId?: string;
  [key: string]: unknown;
}

class Logger {
  private formatMessage(level: LogLevel, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const contextStr = context
      ? ' ' +
        Object.entries(context)
          .map(([key, value]) => `${key}=${value}`)
          .join(' ')
      : '';
    return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;
  }

  debug(message: string, context?: LogContext): void {
    console.debug(this.formatMessage('debug', message, context));
  }

  info(message: string, context?: LogContext): void {
    console.info(this.formatMessage('info', message, context));
  }

  warn(message: string, context?: LogContext): void {
    console.warn(this.formatMessage('warn', message, context));
  }

  error(message: string, context?: LogContext, error?: Error): void {
    const errorContext = error
      ? { ...context, error: error.name, errorMessage: error.message }
      : context;
    console.error(this.formatMessage('error', message, errorContext), error);
  }
}

export const logger = new Logger();
