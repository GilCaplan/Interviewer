// Client Test Example
// server/tests/test_client.js

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import App from '../../Client/src/App';
import FeatureList from '../../Client/src/components/FeatureList';
import FeaturePage from '../../Client/src/components/FeaturePage';

// Setup mocks
// Mock useParams for FeaturePage tests
jest.mock('react-router-dom', () => {
  const originalModule = jest.requireActual('react-router-dom');
  return {
    ...originalModule,
    useParams: jest.fn(() => ({ featureId: '0' })),
    // Use a real Link component for BrowserRouter tests
    Link: ({ children, to, ...props }) =>
      <a href={to} {...props}>{children}</a>
  };
});

// Mock fetch to avoid actual API calls during tests
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      name: 'Interview Process Assistant',
      version: '0.1.0',
      features: [
        'Practice programming problems',
        'Logical puzzles/riddles',
        'Interview questions'
      ]
    }),
  })
);

// Group 1: Original App Component Tests
describe('App Component', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('renders app title', async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    const titleElement = screen.getByText(/Interview Process Assistant/i);
    expect(titleElement).toBeInTheDocument();
  });

  test('fetches and displays API data', async () => {
    render(<BrowserRouter><App /></BrowserRouter>);
    expect(screen.getByText(/loading application information/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/version: 0.1.0/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/practice programming problems/i)).toBeInTheDocument();
    expect(screen.getByText(/logical puzzles\/riddles/i)).toBeInTheDocument();
    expect(screen.getByText(/interview questions/i)).toBeInTheDocument();
  });

  test('handles API error gracefully', async () => {
    // Mock a failed API request
    fetch.mockImplementationOnce(() =>
      Promise.reject(new Error('API error'))
    );

    render(<BrowserRouter><App /></BrowserRouter>);

    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText(/could not connect to the server/i)).toBeInTheDocument();
    });

    // Check that fallback features are displayed
    expect(screen.getByText(/using fallback data for demo purposes/i)).toBeInTheDocument();
  });
});

// Group 2: Feature List Component Tests
describe('FeatureList Component', () => {
  const mockFeatures = [
    { name: 'Test Feature 1', description: 'Description 1' },
    { name: 'Test Feature 2', description: 'Description 2' },
  ];

  test('renders all features correctly', () => {
    render(
      <BrowserRouter>
        <FeatureList features={mockFeatures} />
      </BrowserRouter>
    );

    // Check for heading
    expect(screen.getByText('Available Features')).toBeInTheDocument();

    // Check feature titles and descriptions
    expect(screen.getByText('Test Feature 1')).toBeInTheDocument();
    expect(screen.getByText('Test Feature 2')).toBeInTheDocument();
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
  });

  test('renders the correct number of feature cards', () => {
    render(
      <BrowserRouter>
        <FeatureList features={mockFeatures} />
      </BrowserRouter>
    );

    // Check count of feature cards
    const featureCards = screen.getAllByRole('link');
    expect(featureCards).toHaveLength(2);
  });

  test('each feature card has the correct link', () => {
    render(
      <BrowserRouter>
        <FeatureList features={mockFeatures} />
      </BrowserRouter>
    );

    // Check links for feature cards
    const featureLinks = screen.getAllByRole('link');
    expect(featureLinks[0]).toHaveAttribute('href', '/feature/0');
    expect(featureLinks[1]).toHaveAttribute('href', '/feature/1');
  });

  test('handles empty features array gracefully', () => {
    render(
      <BrowserRouter>
        <FeatureList features={[]} />
      </BrowserRouter>
    );

    // Check that the component still renders without features
    expect(screen.getByText('Available Features')).toBeInTheDocument();
    const featureCards = screen.queryAllByRole('link');
    expect(featureCards).toHaveLength(0);
  });
});

// Group 3: Feature Page Component Tests
describe('FeaturePage Component', () => {
  const mockFeatures = [
    { name: 'Programming problems', description: 'Coding challenges' },
    { name: 'Logical puzzles', description: 'Brain teasers' },
    { name: 'Interview questions', description: 'Technical questions' },
    { name: 'Behavioral questions', description: 'STAR method responses' },
    { name: 'Case studies', description: 'Business cases' },
    { name: 'Mock interviews', description: 'Practice interviews' }
  ];

  test('renders programming feature page correctly', () => {
    // Set the mock implementation for this test
    require('react-router-dom').useParams.mockReturnValue({ featureId: '0' });

    render(<FeaturePage features={mockFeatures} />);

    expect(screen.getByText('Programming problems')).toBeInTheDocument();
    expect(screen.getByText(/Enhance your coding skills/i)).toBeInTheDocument();
  });

  test('renders puzzle feature page correctly', () => {
    // Override mock for this test
    require('react-router-dom').useParams.mockReturnValue({ featureId: '1' });

    render(<FeaturePage features={mockFeatures} />);

    expect(screen.getByText('Logical puzzles')).toBeInTheDocument();
    expect(screen.getByText(/Sharpen your logical thinking/i)).toBeInTheDocument();
  });

  test('contains a back button', () => {
    require('react-router-dom').useParams.mockReturnValue({ featureId: '0' });

    render(<FeaturePage features={mockFeatures} />);
    const backButton = screen.getByText('Back to Features');
    expect(backButton).toBeInTheDocument();
    expect(backButton.closest('a')).toHaveAttribute('href', '/');
  });

  test('renders "Feature Not Found" when feature ID is invalid', () => {
    // Override mock for this test
    require('react-router-dom').useParams.mockReturnValue({ featureId: '99' });

    render(<FeaturePage features={mockFeatures} />);
    expect(screen.getByText('Feature Not Found')).toBeInTheDocument();
  });
});

// Group 4: Routing Tests
describe('App Routing', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('routes to feature page correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/feature/0']}>
        <App />
      </MemoryRouter>
    );

    // Initial loading state
    expect(screen.getByText(/loading application information/i)).toBeInTheDocument();

    // Wait for data to load
    await waitFor(() => {
      // Since we're using the real components, look for feature page content
      expect(screen.getByText(/back to features/i)).toBeInTheDocument();
    });
  });
});

// Group 5: Security Tests
describe('Security Tests', () => {
  test('FeaturePage sanitizes malicious feature IDs', () => {
    // Test with script injection attempt in URL
    require('react-router-dom').useParams.mockReturnValue({
      featureId: '<script>alert("XSS")</script>'
    });

    render(<FeaturePage features={[{ name: 'Safe Feature', description: 'Safe Description' }]} />);

    // Should show Feature Not Found page for non-numeric inputs
    expect(screen.getByText('Feature Not Found')).toBeInTheDocument();
  });

  test('FeaturePage handles feature content with HTML securely', () => {
    // Create a feature with potentially unsafe content
    const unsafeFeatures = [
      {
        name: '<b>Unsafe HTML</b>',
        description: '<img src="x" onerror="alert(\'XSS\')">'
      }
    ];

    require('react-router-dom').useParams.mockReturnValue({ featureId: '0' });

    render(<FeaturePage features={unsafeFeatures} />);

    // Content should be rendered as text, not interpreted as HTML
    expect(screen.getByText('<b>Unsafe HTML</b>')).toBeInTheDocument();
  });
});