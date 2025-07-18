import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Configure marked options
marked.setOptions({
  breaks: true, // Convert \n to <br>
  gfm: true, // GitHub Flavored Markdown
  headerIds: false, // Don't add IDs to headers
  mangle: false, // Don't mangle emails
})

// Custom renderer for better styling
const renderer = new marked.Renderer()

// Custom code block renderer with syntax highlighting support
renderer.code = function(code, language) {
  const validLanguage = language && /^[a-zA-Z0-9-_]+$/.test(language)
  const langClass = validLanguage ? ` class="language-${language}"` : ''
  
  // Escape HTML in code content to prevent XSS
  const escapedCode = DOMPurify.sanitize(code, { ALLOWED_TAGS: [] })
  
  return `<pre><code${langClass}>${escapedCode}</code></pre>`
}

// Custom link renderer with security
renderer.link = function(href, title, text) {
  const cleanHref = DOMPurify.sanitize(href)
  const titleAttr = title ? ` title="${DOMPurify.sanitize(title)}"` : ''
  return `<a href="${cleanHref}" target="_blank" rel="noopener noreferrer"${titleAttr}>${text}</a>`
}

// Custom list renderer for better styling
renderer.list = function(body, ordered, start) {
  const tag = ordered ? 'ol' : 'ul'
  const startAttr = ordered && start !== 1 ? ` start="${start}"` : ''
  return `<${tag}${startAttr}>\n${body}</${tag}>\n`
}

// Custom paragraph renderer to handle empty lines
renderer.paragraph = function(text) {
  return `<p>${text}</p>\n`
}

marked.use({ renderer })

/**
 * Convert markdown text to safe HTML
 * @param {string} markdown - The markdown text to convert
 * @returns {string} - Safe HTML string
 */
export function markdownToHtml(markdown) {
  if (!markdown) return ''

  try {
    // Custom rule for \boxed{}
    const boxedHtml = markdown.replace(/\\boxed{([^}]+)}/g, '<div class="boxed-answer">$1</div>');

    // Convert markdown to HTML
    const html = marked.parse(boxedHtml)

    // Sanitize HTML to prevent XSS attacks
    const cleanHtml = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br',
        'strong', 'b', 'em', 'i', 'u', 's',
        'ul', 'ol', 'li',
        'blockquote',
        'code', 'pre',
        'a',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr',
        'img',
        'div' // Allow div for the boxed answer
      ],
      ALLOWED_ATTR: [
        'href', 'title', 'target', 'rel',
        'class', 'id',
        'src', 'alt', 'width', 'height',
        'start'
      ],
      ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i
    })

    return cleanHtml
  } catch (error) {
    console.error('Error parsing markdown:', error)
    // Fallback to escaped text
    return DOMPurify.sanitize(markdown)
      .replace(/\n/g, '<br>')
  }
}

/**
 * Simple markdown formatter for basic use cases (fallback)
 * @param {string} text - Text to format
 * @returns {string} - Formatted HTML
 */
export function simpleMarkdown(text) {
  if (!text) return ''
  
  // First sanitize the input text
  const sanitizedText = DOMPurify.sanitize(text, { ALLOWED_TAGS: [] })
  
  return sanitizedText
    // Code blocks
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Links (with URL validation)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
      // Basic URL validation
      const urlPattern = /^https?:\/\//i
      if (urlPattern.test(url)) {
        const cleanUrl = DOMPurify.sanitize(url)
        const cleanText = DOMPurify.sanitize(text)
        return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer">${cleanText}</a>`
      }
      return match // Return original if URL is invalid
    })
    // Line breaks
    .replace(/\n/g, '<br>')
}
