import { ExecutionTrace, ChatQuery } from '../../../services/api';

export interface ThreadInfo {
  id: number;
  title?: string;
  created_at?: string;
}

export interface OrganizationInfo {
  id: number;
  name: string;
}

/**
 * Format execution trace for text export
 */
export const formatExecutionTrace = (trace: ExecutionTrace | undefined): string => {
  if (!trace) return '';

  let output = '\n\n--- Agent Execution Trace ---\n';
  output += `Total Nodes: ${trace.nodes.length}\n`;
  output += `Total Edges: ${trace.edges.length}\n\n`;

  trace.nodes.forEach((node, idx) => {
    output += `${idx + 1}. [${node.type.toUpperCase()}] ${node.name}\n`;
    if (node.metadata) {
      const metadataStr = JSON.stringify(node.metadata, null, 2);
      output += `   Metadata: ${metadataStr}\n`;
    }
  });

  if (trace.edges.length > 0) {
    output += '\n--- Execution Flow ---\n';
    trace.edges.forEach((edge, idx) => {
      output += `${idx + 1}. ${edge.source} → ${edge.target}`;
      if (edge.label) output += ` (${edge.label})`;
      output += '\n';
    });
  }

  return output;
};

/**
 * Export thread as Markdown format
 */
export const exportAsMarkdown = (
  messages: ChatQuery[],
  currentThread: ThreadInfo,
  organizationName: string,
  includeTraces: boolean
): string => {
  let md = `# Conversation: ${currentThread.title || `Thread ${currentThread.id}`}\n\n`;
  md += `**Organization:** ${organizationName}\n`;
  md += `**Created:** ${currentThread.created_at ? new Date(currentThread.created_at).toLocaleString() : 'Unknown'}\n\n`;
  md += '---\n\n';

  messages.forEach((msg, idx) => {
    md += `## Message ${idx + 1}\n\n`;
    md += `**User:** ${msg.message}\n\n`;

    if (msg.files && msg.files.length > 0) {
      md += '**Attached Files:**\n';
      msg.files.forEach(file => {
        md += `- ${file.original_filename}\n`;
      });
      md += '\n';
    }

    if (msg.response) {
      md += `**Assistant:**\n\n${msg.response}\n\n`;
    }

    if (msg.citations && msg.citations.length > 0) {
      md += '**Citations:**\n';
      msg.citations.forEach(citation => {
        md += `- ${citation.title || citation.url || citation.description || 'Citation'}\n`;
      });
      md += '\n';
    }

    if (msg.recommendations && msg.recommendations.length > 0) {
      md += '**Recommendations:**\n';
      msg.recommendations.forEach(rec => {
        md += `- ${rec}\n`;
      });
      md += '\n';
    }

    if (includeTraces && msg.execution_trace) {
      md += formatExecutionTrace(msg.execution_trace);
      md += '\n';
    }

    md += `*Timestamp: ${msg.created_at ? new Date(msg.created_at).toLocaleString() : 'Unknown'}*\n\n`;
    md += '---\n\n';
  });

  return md;
};

/**
 * Export thread as JSON format
 */
export const exportAsJSON = (
  messages: ChatQuery[],
  currentThread: ThreadInfo,
  organizationName: string,
  includeTraces: boolean
): string => {
  const exportData = {
    thread: {
      id: currentThread.id,
      title: currentThread.title,
      created_at: currentThread.created_at,
      organization: organizationName,
    },
    messages: messages.map(msg => ({
      id: msg.id,
      message: msg.message,
      response: msg.response,
      created_at: msg.created_at,
      files: msg.files?.map(f => ({
        filename: f.original_filename,
        size: f.file_size,
      })),
      citations: msg.citations,
      recommendations: msg.recommendations,
      execution_times: msg.execution_times,
      ...(includeTraces && msg.execution_trace ? { execution_trace: msg.execution_trace } : {}),
    })),
  };

  return JSON.stringify(exportData, null, 2);
};

/**
 * Export thread as plain text format
 */
export const exportAsText = (
  messages: ChatQuery[],
  currentThread: ThreadInfo,
  organizationName: string,
  includeTraces: boolean
): string => {
  let text = `Conversation: ${currentThread.title || `Thread ${currentThread.id}`}\n`;
  text += `Organization: ${organizationName}\n`;
  text += `Created: ${currentThread.created_at ? new Date(currentThread.created_at).toLocaleString() : 'Unknown'}\n\n`;
  text += '='.repeat(50) + '\n\n';

  messages.forEach((msg, idx) => {
    text += `Message ${idx + 1}\n`;
    text += '-'.repeat(30) + '\n';
    text += `User: ${msg.message}\n\n`;

    if (msg.files && msg.files.length > 0) {
      text += 'Attached Files:\n';
      msg.files.forEach(file => {
        text += `  - ${file.original_filename}\n`;
      });
      text += '\n';
    }

    if (msg.response) {
      text += `Assistant: ${msg.response}\n\n`;
    }

    if (msg.citations && msg.citations.length > 0) {
      text += 'Citations:\n';
      msg.citations.forEach(citation => {
        text += `  - ${citation.title || citation.url || citation.description || 'Citation'}\n`;
      });
      text += '\n';
    }

    if (msg.recommendations && msg.recommendations.length > 0) {
      text += 'Recommendations:\n';
      msg.recommendations.forEach(rec => {
        text += `  - ${rec}\n`;
      });
      text += '\n';
    }

    if (includeTraces && msg.execution_trace) {
      text += formatExecutionTrace(msg.execution_trace);
      text += '\n';
    }

    text += `Timestamp: ${msg.created_at ? new Date(msg.created_at).toLocaleString() : 'Unknown'}\n\n`;
    text += '='.repeat(50) + '\n\n';
  });

  return text;
};

/**
 * Download content as a file
 */
export const downloadAsFile = (
  content: string,
  filename: string,
  mimeType: string
): void => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
