import { AboutDialog } from './components/AboutDialog';
import { BuildFooter } from './components/BuildFooter';

export default function App() {
  return (
    <>
      <main
        style={{
          fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial',
          padding: 24,
        }}
      >
        <AboutDialog />
        <h1 style={{ marginTop: 0 }}>Hello, World! 👋</h1>
        <p>
          This is your AI dev stack template. Click <strong>About</strong> to see build/version
          info.
        </p>
      </main>
      <BuildFooter />
    </>
  );
}
