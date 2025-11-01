/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      // Add any custom rules here
    },
  },
  {
    ignores: ['.next/', 'node_modules/', 'out/', 'dist/', 'build/'],
  },
];

export default eslintConfig;
