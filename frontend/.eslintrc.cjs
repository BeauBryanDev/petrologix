// ESLint 8 classic config (not flat) //
// typescript-eslint 7 in package.json.
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  plugins: ['react-refresh'],
  // vite-env.d.ts is a triple-slash reference and nothing else -- it has no
  // lintable code and does not parse under these options.
  ignorePatterns: ['dist', 'node_modules', '.eslintrc.cjs', '*.config.js', 'vite-env.d.ts'],
  rules: {
    // allowConstantExport keeps const-only modules such as
    // wellog/lithologyPalette.ts from tripping this under --max-warnings 0.
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
  },
};
