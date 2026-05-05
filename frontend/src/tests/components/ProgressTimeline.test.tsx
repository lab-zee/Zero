import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import ProgressTimeline, { ProgressUpdate } from '../../components/ProgressTimeline';

const renderWithChakra = (ui: React.ReactElement) => {
  return render(<ChakraProvider>{ui}</ChakraProvider>);
};

describe('ProgressTimeline', () => {
  const mockUpdates: ProgressUpdate[] = [
    {
      agent_name: 'Director',
      message: 'Delegating to Market Research',
      type: 'delegation',
      delegate_to: 'Market Research'
    },
    {
      agent_name: 'Market Research',
      message: 'Analyzing market trends',
      type: 'tool_result',
      tool_name: 'web_search'
    },
  ];

  it('renders nothing when no updates', () => {
    renderWithChakra(
      <ProgressTimeline updates={[]} />
    );
    expect(screen.queryByText('Reasoning Progress')).not.toBeInTheDocument();
  });

  it('renders progress updates', () => {
    renderWithChakra(
      <ProgressTimeline updates={mockUpdates} />
    );

    expect(screen.getByText('Reasoning Progress')).toBeInTheDocument();
    expect(screen.getByText('Director')).toBeInTheDocument();
    expect(screen.getByText('Delegating to Market Research')).toBeInTheDocument();
  });

  it('shows live badge when streaming', () => {
    renderWithChakra(
      <ProgressTimeline updates={mockUpdates} isStreaming={true} />
    );

    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('can be collapsed and expanded', () => {
    renderWithChakra(
      <ProgressTimeline updates={mockUpdates} />
    );

    const collapseButton = screen.getByLabelText('Collapse');
    fireEvent.click(collapseButton);

    // After collapse, should show expand button
    expect(screen.getByLabelText('Expand')).toBeInTheDocument();
  });

  it('displays delegation type correctly', () => {
    renderWithChakra(
      <ProgressTimeline updates={mockUpdates} />
    );

    expect(screen.getAllByText('Market Research').length).toBeGreaterThan(0);
  });

  it('displays tool result type correctly', () => {
    renderWithChakra(
      <ProgressTimeline updates={mockUpdates} />
    );

    expect(screen.getByText('web_search')).toBeInTheDocument();
  });
});
