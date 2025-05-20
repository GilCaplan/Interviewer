// Client Test Example
// tests/test_client.js

import { render, screen, waitFor } from '@testing-library/react';
import App from '../Client/src/App';

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

describe('App Component', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('renders app title', async () => {
    render(<App />);
    const titleElement = screen.getByText(/Interview Process Assistant/i);
    expect(titleElement).toBeInTheDocument();
  });

  test('fetches and displays API data', async () => {
    render(<App />);
    expect(screen.getByText(/loading application information/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/version: 0.1.0/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/practice programming problems/i)).toBeInTheDocument();
    expect(screen.getByText(/logical puzzles\/riddles/i)).toBeInTheDocument();
    expect(screen.getByText(/interview questions/i)).toBeInTheDocument();
  });
});