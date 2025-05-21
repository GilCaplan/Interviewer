// Simple markdown to HTML converter for challenge descriptions
export const markdownToHtml = (markdown) => {
  if (!markdown) return '';

  // Convert code blocks with syntax highlighting
  let html = markdown
    .replace(/```([a-z]*)\n([\s\S]*?)\n```/g, '<pre class="code-block"><code class="language-$1">$2</code></pre>')

    // Convert inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')

    // Convert headings
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')

    // Convert bold text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')

    // Convert italic text
    .replace(/\*(.*?)\*/g, '<em>$1</em>')

    // Convert lists
    .replace(/^\s*\n\* (.*)/gm, '<ul>\n<li>$1</li>')
    .replace(/^(\* )(.*)/gm, '<li>$2</li>')
    .replace(/^\s*\n- (.*)/gm, '<ul>\n<li>$1</li>')
    .replace(/^(- )(.*)/gm, '<li>$2</li>')
    .replace(/^\s*\n\d+\. (.*)/gm, '<ol>\n<li>$1</li>')
    .replace(/^(\d+\. )(.*)/gm, '<li>$2</li>')

    // Convert paragraphs
    .replace(/^\s*\n\n+/gm, '</p><p>')

    // Convert line breaks
    .replace(/^(.+)\n+/gm, '$1<br />')

    // Clean up empty tags
    .replace(/<\/ul><p><\/p><ul>/g, '')
    .replace(/<\/ol><p><\/p><ol>/g, '');

  // Wrap the content in paragraphs if not already wrapped
  if (!html.match(/^<p>/)) {
    html = '<p>' + html + '</p>';
  }

  return html;
};

// Sanitize Markdown input
export const sanitizeMarkdown = (input) => {
  if (!input) return '';

  // Remove potentially dangerous HTML
  return input
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/<link\b[^<]*(?:(?!<\/link>)<[^<]*)*<\/link>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<[^>]*on\w+\s*=\s*("|\')[^>]*>/gi, match => match.replace(/on\w+\s*=\s*("|\')[^>]*/gi, ''));
};

// Convert HTML entities to prevent XSS
export const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
};

// Process markdown for safe display
export const processSafeMarkdown = (markdown) => {
  if (!markdown) return '';
  const sanitized = sanitizeMarkdown(markdown);
  return markdownToHtml(sanitized);
};