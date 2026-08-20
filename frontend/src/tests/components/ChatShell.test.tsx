import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AnswerModeSelector from '../../components/AnswerModeSelector';
import ExecutionTracePanel from '../../components/ExecutionTracePanel';

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, username: 'test' } }),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <ChakraProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    </ChakraProvider>
  );
};

describe('AnswerModeSelector', () => {
  it('renders crew-provided modes', () => {
    render(
      <AnswerModeSelector
        value="light"
        onChange={() => {}}
        modes={[
          { id: 'summary', label: 'Quick', description: 'Brief' },
          { id: 'light', label: 'Full', description: 'Balanced' },
        ]}
      />,
      { wrapper }
    );
    expect(screen.getByText('Quick')).toBeInTheDocument();
    expect(screen.getByText('Full')).toBeInTheDocument();
  });
});

describe('ExecutionTracePanel', () => {
  it('shows LLM prompts toggle when prompts exist', () => {
    render(
      <ExecutionTracePanel
        trace={{
          nodes: [{ id: 'a1', type: 'agent', name: 'Director' }],
          edges: [],
        }}
        progressUpdates={[]}
        llmPrompts={[
          {
            agent_id: 'director',
            agent_name: 'Director',
            model: 'gpt-4o',
            iteration: 0,
            messages: [{ role: 'system', content: 'You are the director.' }],
            timestamp: new Date().toISOString(),
          },
        ]}
      />,
      { wrapper }
    );
    expect(screen.getByText(/LLM prompts/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/LLM prompts/i));
  });

  it('starts collapsed when not streaming', () => {
    render(
      <ExecutionTracePanel
        trace={{ nodes: [], edges: [] }}
        isStreaming={false}
      />,
      { wrapper }
    );
    expect(screen.getByLabelText(/Expand/i)).toBeInTheDocument();
  });
});
