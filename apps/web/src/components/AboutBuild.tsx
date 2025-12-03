import { buildInfo } from '../buildInfo';

export function AboutBuild() {
  return (
    <div>
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
  );
}
