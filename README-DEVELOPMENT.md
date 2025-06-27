# Development Guide

This guide covers the development setup, tooling, and best practices for the Thyme project.

## Prerequisites

- **Node.js**: Version 20.11.1 or higher
- **Yarn**: Version 1.22.22 or higher
- **Volta**: For automatic Node.js and Yarn version management

## Quick Start

1. **Install Volta** (if not already installed):
   ```bash
   curl https://get.volta.sh | bash
   ```

2. **Clone and setup the project**:
   ```bash
   git clone <repository-url>
   cd thyme
   yarn install
   ```

3. **Verify your environment**:
   ```bash
   yarn check-deps
   ```

## Development Scripts

### Build and Development
- `yarn build` - Compile TypeScript to JavaScript
- `yarn dev` - Watch mode for development
- `yarn clean` - Remove build artifacts
- `yarn rebuild` - Clean and rebuild

### Code Quality
- `yarn lint` - Run ESLint to check code quality
- `yarn lint:fix` - Fix auto-fixable ESLint issues
- `yarn format` - Format code with Prettier
- `yarn format:check` - Check if code is properly formatted
- `yarn type-check` - Run TypeScript type checking

### Testing
- `yarn test` - Run all tests
- `yarn test:watch` - Run tests in watch mode
- `yarn test:coverage` - Run tests with coverage report

### Utilities
- `yarn check-deps` - Check required dependencies
- `yarn sql-queries` - Run SQL queries
- `yarn help` - Show available commands
- `yarn info` - Show project information

## Code Quality Tools

### ESLint
ESLint is configured with TypeScript support and enforces:
- TypeScript best practices
- Import/export organization
- Code style consistency
- Common JavaScript/Node.js rules

**Configuration**: `.eslintrc.js`

### Prettier
Prettier handles code formatting with:
- Consistent code style across the project
- Integration with ESLint
- Automatic formatting on save (with editor setup)

**Configuration**: `.prettierrc`

### TypeScript
Strict TypeScript configuration with:
- Modern ES2022 target
- Strict type checking
- Path mapping for clean imports
- Declaration file generation

**Configuration**: `tsconfig.json`

### Jest
Testing framework with:
- TypeScript support via ts-jest
- Coverage reporting
- Mocking capabilities
- Test utilities

**Configuration**: `jest.config.js`

## Git Hooks

### Pre-commit Hook
Automatically runs on every commit:
- Lints staged TypeScript files
- Formats code with Prettier
- Prevents commits with linting errors

### Commit Message Hook
Validates commit messages follow conventional format:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `style: formatting changes`
- `refactor: code refactoring`
- `test: add tests`
- `chore: maintenance tasks`

## Editor Setup

### VS Code (Recommended)
Install these extensions for the best development experience:

1. **ESLint** - ESLint integration
2. **Prettier** - Code formatter
3. **TypeScript Importer** - Auto-import TypeScript modules
4. **GitLens** - Git integration
5. **Jest** - Jest testing support

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true
}
```

### Other Editors
- **WebStorm**: Built-in TypeScript, ESLint, and Prettier support
- **Vim/Neovim**: Use ALE or coc.nvim for TypeScript support
- **Emacs**: Use lsp-mode for TypeScript support

## Project Structure

```
thyme/
├── src/                    # Source code
├── scripts/               # Build and utility scripts
│   └── __tests__/        # Script tests
├── types/                # TypeScript type definitions
├── dist/                 # Compiled JavaScript (generated)
├── coverage/             # Test coverage reports (generated)
├── .husky/               # Git hooks
├── templates/            # HTML templates
├── static/               # Static assets
└── sql/                  # SQL migration files
```

## Development Workflow

1. **Start Development**:
   ```bash
   yarn dev
   ```

2. **Make Changes**: Edit TypeScript files in `src/` or `scripts/`

3. **Run Tests**:
   ```bash
   yarn test
   ```

4. **Check Code Quality**:
   ```bash
   yarn lint
   yarn format:check
   yarn type-check
   ```

5. **Commit Changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

## Testing

### Writing Tests
- Place test files next to source files with `.test.ts` or `.spec.ts` extension
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies

**Example Test**:
```typescript
import { myFunction } from '../myModule';

describe('myFunction', () => {
  it('should return expected result', () => {
    // Arrange
    const input = 'test';
    
    // Act
    const result = myFunction(input);
    
    // Assert
    expect(result).toBe('expected');
  });
});
```

### Running Tests
- `yarn test` - Run all tests once
- `yarn test:watch` - Run tests in watch mode
- `yarn test:coverage` - Generate coverage report

## TypeScript Best Practices

### Type Definitions
- Use interfaces for object shapes
- Use type aliases for unions and complex types
- Export types from `types/` directory
- Use strict TypeScript settings

### Import/Export
- Use named exports for functions and classes
- Use default exports sparingly
- Organize imports: built-in → external → internal
- Use path mapping for clean imports

### Error Handling
- Use custom error classes
- Provide meaningful error messages
- Include error codes for API responses
- Handle async errors properly

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the coding standards
4. **Run tests**: `yarn test`
5. **Check code quality**: `yarn lint && yarn format:check`
6. **Commit your changes**: Use conventional commit format
7. **Push to your fork**: `git push origin feature/amazing-feature`
8. **Create a Pull Request**

## Troubleshooting

### Common Issues

**TypeScript compilation errors**:
```bash
yarn type-check
```

**ESLint errors**:
```bash
yarn lint:fix
```

**Prettier formatting issues**:
```bash
yarn format
```

**Test failures**:
```bash
yarn test --verbose
```

### Performance Issues
- Use `yarn dev` for development (faster compilation)
- Use `yarn build` for production builds
- Check TypeScript configuration for optimization settings

### Dependency Issues
- Clear yarn cache: `yarn cache clean`
- Remove node_modules: `rm -rf node_modules && yarn install`
- Check Volta versions: `volta list`

## Additional Resources

- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [ESLint Rules](https://eslint.org/docs/rules/)
- [Prettier Options](https://prettier.io/docs/en/options.html)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Conventional Commits](https://www.conventionalcommits.org/) 