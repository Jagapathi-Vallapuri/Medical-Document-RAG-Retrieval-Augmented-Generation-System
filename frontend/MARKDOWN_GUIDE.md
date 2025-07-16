# Enhanced Markdown Support Installation Guide

## 📦 Installation

To install the enhanced markdown support, run the following command in your frontend directory:

```bash
npm install marked dompurify
```

## 🚀 What's Improved

### Before (Custom Regex):
- ❌ Limited markdown support
- ❌ No security sanitization  
- ❌ Poor handling of complex structures
- ❌ No standards compliance
- ❌ Hard to maintain

### After (Marked.js + DOMPurify):
- ✅ Full GitHub Flavored Markdown support
- ✅ XSS protection with DOMPurify
- ✅ Proper parsing of complex structures
- ✅ Standards compliant
- ✅ Easy to extend and maintain

## 📋 Supported Markdown Features

### Text Formatting:
- **Bold**: `**text**` or `__text__`
- *Italic*: `*text*` or `_text_`
- ~~Strikethrough~~: `~~text~~`
- `Inline code`: `` `code` ``

### Headers:
```markdown
# H1 Header
## H2 Header  
### H3 Header
#### H4 Header
##### H5 Header
###### H6 Header
```

### Lists:
```markdown
- Unordered list item 1
- Unordered list item 2
  - Nested item

1. Ordered list item 1
2. Ordered list item 2
   1. Nested item
```

### Code Blocks:
````markdown
```javascript
function hello() {
    console.log("Hello, World!");
}
```
````

### Tables:
```markdown
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

### Links & Images:
```markdown
[Link text](https://example.com)
![Alt text](image-url.jpg)
```

### Blockquotes:
```markdown
> This is a blockquote
> It can span multiple lines
```

### Horizontal Rules:
```markdown
---
```

## 🔒 Security Features

- **XSS Protection**: All HTML is sanitized using DOMPurify
- **Safe Links**: External links open in new tabs with security attributes
- **Content Filtering**: Only allowed HTML tags and attributes are permitted
- **URI Validation**: Only safe protocols (https, http, mailto) are allowed

## 🎨 Styling

The CSS has been enhanced to support:
- Responsive tables
- Beautiful blockquotes
- Syntax-highlighted code blocks
- Proper spacing and typography
- Dark/light theme support for user vs assistant messages

## 🔧 Configuration

The markdown parser is configured in `/src/utils/markdown.js` with:
- GitHub Flavored Markdown enabled
- Line breaks converted to `<br>` tags
- Custom renderers for security and styling
- Sanitization rules for safety

## 📈 Performance

- **Marked.js**: ~50KB minified, very fast parsing
- **DOMPurify**: ~45KB minified, secure sanitization
- **Total**: ~95KB additional bundle size for professional markdown support

## 🛡️ Fallback

If the libraries fail to load, there's a `simpleMarkdown()` function that provides basic formatting as a fallback.

## 🚀 Usage Example

In your RAG pipeline, you can now return rich markdown:

```python
return {
    "message": """
# Analysis Results

## Key Findings:
- **Important discovery**: The data shows significant trends
- *Secondary insight*: Additional patterns were identified

### Code Example:
```python
def analyze_data(data):
    return processed_results
```

### Summary Table:
| Metric | Value | Status |
|--------|-------|--------|
| Accuracy | 95% | ✅ Good |
| Speed | 1.2s | ⚠️ Needs improvement |

> **Note**: These results are based on the latest analysis.

For more details, see [our documentation](https://example.com).
    """
}
```

This will be beautifully rendered in the chat interface with proper styling, security, and responsiveness.
