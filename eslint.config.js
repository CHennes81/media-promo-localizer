import prettier from 'eslint-config-prettier';

export default [
  {
    files: ['**/*.{js,ts,tsx}'],
    ignores: ['dist/**', 'build/**', 'coverage/**', 'node_modules/**'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    rules: {},
  },
  prettier,
];
