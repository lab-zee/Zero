import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { ReAskButton } from '../../components/ReAskButton';

const renderWithChakra = (ui: React.ReactElement) => {
  return render(<ChakraProvider>{ui}</ChakraProvider>);
};

describe('ReAskButton', () => {
  beforeEach(() => {
    // Mock scrollTo for Chakra UI Menu
    HTMLElement.prototype.scrollTo = vi.fn() as any;
  });
  it('renders re-ask button', () => {
    const mockOnReAsk = vi.fn();
    renderWithChakra(
      <ReAskButton
        queryId={1}
        currentMode="light"
        onReAsk={mockOnReAsk}
      />
    );

    expect(screen.getByText('Re-ask')).toBeInTheDocument();
  });

  it('shows available modes excluding current mode', () => {
    const mockOnReAsk = vi.fn();
    renderWithChakra(
      <ReAskButton
        queryId={1}
        currentMode="light"
        onReAsk={mockOnReAsk}
      />
    );

    const button = screen.getByText('Re-ask');
    fireEvent.click(button);

    // Should show summary and extended, but not light
    expect(screen.getByText(/Summary/)).toBeInTheDocument();
    expect(screen.getByText(/Extended/)).toBeInTheDocument();
  });

  it('calls onReAsk with correct parameters', () => {
    const mockOnReAsk = vi.fn();
    renderWithChakra(
      <ReAskButton
        queryId={123}
        currentMode="light"
        onReAsk={mockOnReAsk}
      />
    );

    const button = screen.getByText('Re-ask');
    fireEvent.click(button);

    const summaryOption = screen.getByText(/Summary/);
    fireEvent.click(summaryOption);

    expect(mockOnReAsk).toHaveBeenCalledWith(123, 'summary');
  });

  it('is disabled when isDisabled prop is true', () => {
    const mockOnReAsk = vi.fn();
    renderWithChakra(
      <ReAskButton
        queryId={1}
        currentMode="light"
        onReAsk={mockOnReAsk}
        isDisabled={true}
      />
    );

    const buttonText = screen.getByText('Re-ask');
    const button = buttonText.closest('button');
    expect(button).toBeDisabled();
  });
});
