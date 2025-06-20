# Thyme

A modern task management application built with [TrailBase](https://trailbase.io/), React, TypeScript, and Vite.

## 🚀 Features

- **Modern Stack**: Built with React 18, TypeScript, and Vite
- **TrailBase Backend**: Fast, type-safe backend with built-in authentication
- **Beautiful UI**: Modern design with Tailwind CSS and Lucide icons
- **Task Management**: Create, organize, and track tasks with priorities and due dates
- **Authentication**: Secure user authentication with JWT tokens
- **Responsive**: Works perfectly on desktop and mobile devices

## 🛠️ Tech Stack

- **Frontend**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS, Lucide React icons
- **Backend**: TrailBase (Rust, SQLite, V8)
- **Testing**: Vitest, React Testing Library
- **Linting**: ESLint, Prettier
- **CI/CD**: GitHub Actions

## 📦 Installation

### Prerequisites

- Node.js 16+ 
- npm 8+
- TrailBase binary

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/thyme.git
   cd thyme
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Install TrailBase**
   ```bash
   # Download TrailBase binary for your platform
   # Visit: https://trailbase.io/
   ```

4. **Start TrailBase backend**
   ```bash
   # Run TrailBase with the configuration
   trailbase serve --config trailbase.toml
   ```

5. **Start the development server**
   ```bash
   npm run dev
   ```

6. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## 🔧 Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Fix linting issues
npm run lint:fix

# Check formatting
npm run format:check

# Format code
npm run format

# Type checking
npm run type-check

# Run all validations
npm run validate
```

## 📝 Scripts

| Script | Description |
|--------|-------------|
| `dev` | Start development server |
| `build` | Build for production |
| `preview` | Preview production build |
| `test` | Run tests |
| `test:ui` | Run tests with UI |
| `test:coverage` | Run tests with coverage |
| `lint` | Run ESLint |
| `lint:fix` | Fix ESLint issues |
| `format` | Format code with Prettier |
| `format:check` | Check code formatting |
| `type-check` | Run TypeScript type checking |
| `validate` | Run all validations |

## 🏗️ Project Structure

```
thyme/
├── src/
│   ├── components/     # Reusable React components
│   ├── contexts/       # React contexts (Auth, Tasks)
│   ├── lib/           # Utility libraries and API
│   ├── pages/         # Page components
│   ├── test/          # Test utilities and setup
│   ├── types/         # TypeScript type definitions
│   ├── App.tsx        # Main App component
│   ├── main.tsx       # Application entry point
│   └── index.css      # Global styles
├── .github/           # GitHub Actions workflows
├── .husky/            # Git hooks
├── public/            # Static assets
├── trailbase.toml     # TrailBase configuration
├── vite.config.ts     # Vite configuration
├── vitest.config.ts   # Vitest configuration
└── package.json       # Dependencies and scripts
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `npm run validate`
5. Commit your changes: `npm run commit`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build process or auxiliary tool changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [TrailBase](https://trailbase.io/) for the amazing backend
- [React](https://reactjs.org/) for the frontend framework
- [Vite](https://vitejs.dev/) for the build tool
- [Tailwind CSS](https://tailwindcss.com/) for the styling
- [Lucide](https://lucide.dev/) for the icons

## 📞 Support

If you have any questions or need help, please:

1. Check the [documentation](https://github.com/yourusername/thyme/wiki)
2. Search [existing issues](https://github.com/yourusername/thyme/issues)
3. Create a [new issue](https://github.com/yourusername/thyme/issues/new)

## 🚀 Deployment

### Vercel

1. Connect your GitHub repository to Vercel
2. Set environment variables:
   - `VITE_API_URL`: Your TrailBase API URL
3. Deploy!

### Netlify

1. Connect your GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Set environment variables
5. Deploy!

### Manual Deployment

1. Build the application: `npm run build`
2. Upload the `dist` folder to your web server
3. Configure your server to serve the static files

## 🔒 Security

If you discover a security vulnerability, please:

1. **Do not** create a public issue
2. Email us at security@yourdomain.com
3. We'll respond within 48 hours

## 📊 Status

[![CI](https://github.com/yourusername/thyme/workflows/CI/badge.svg)](https://github.com/yourusername/thyme/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://reactjs.org/)