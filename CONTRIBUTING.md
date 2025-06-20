# Contributing to Thyme

Thank you for your interest in contributing to Thyme! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to see if the problem has already been reported. When creating a bug report, include:

- A clear and descriptive title
- Steps to reproduce the problem
- Expected behavior
- Actual behavior
- Screenshots if applicable
- Environment information (OS, browser, etc.)

### Suggesting Enhancements

We welcome feature requests! When suggesting enhancements:

- Use a clear and descriptive title
- Provide a detailed description of the proposed functionality
- Explain why this enhancement would be useful
- Include mockups or examples if possible

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `npm run validate`
5. **Commit your changes**: `npm run commit`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 🛠️ Development Setup

### Prerequisites

- Node.js 16+
- npm 8+
- Git

### Local Development

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/thyme.git
   cd thyme
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up Git hooks**
   ```bash
   npm run prepare
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

### Code Quality

We use several tools to maintain code quality:

- **ESLint**: Code linting
- **Prettier**: Code formatting
- **TypeScript**: Type checking
- **Vitest**: Unit testing
- **Husky**: Git hooks

Run quality checks:
```bash
npm run validate
```

## 📝 Code Style

### TypeScript

- Use TypeScript for all new code
- Provide proper type definitions
- Avoid `any` type when possible
- Use interfaces for object shapes

### React

- Use functional components with hooks
- Follow React best practices
- Use proper prop types
- Implement proper error boundaries

### CSS/Styling

- Use Tailwind CSS for styling
- Follow mobile-first responsive design
- Maintain consistent spacing and colors
- Use semantic class names

### File Naming

- Use PascalCase for components: `UserProfile.tsx`
- Use camelCase for utilities: `apiClient.ts`
- Use kebab-case for files: `user-profile.css`

## 🧪 Testing

### Writing Tests

- Write tests for all new features
- Use React Testing Library for component tests
- Test user interactions, not implementation details
- Aim for good test coverage

### Running Tests

```bash
# Run all tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### Test Structure

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Component } from './Component'

describe('Component', () => {
  it('should render correctly', () => {
    render(<Component />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

## 📋 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Commit Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test changes
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes

### Commit Format

```
type(scope): description

[optional body]

[optional footer]
```

### Examples

```
feat(auth): add user registration functionality
fix(ui): resolve button alignment issue
docs(readme): update installation instructions
test(components): add unit tests for UserProfile
```

## 🔄 Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** if applicable
5. **Request review** from maintainers

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] Tests pass and coverage is adequate
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format
- [ ] PR description clearly describes the changes

## 🏷️ Issue Labels

We use the following labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on

## 📞 Getting Help

If you need help with your contribution:

1. Check the [documentation](README.md)
2. Search [existing issues](https://github.com/yourusername/thyme/issues)
3. Ask in the [discussions](https://github.com/yourusername/thyme/discussions)
4. Create an issue with the `question` label

## 🎉 Recognition

Contributors will be recognized in:

- The project's README
- Release notes
- GitHub contributors page

## 📄 License

By contributing to Thyme, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You

Thank you for contributing to Thyme! Your contributions help make this project better for everyone. 