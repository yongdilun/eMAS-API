const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Colors / Borders
  content = content.replace(/bg-white dark:bg-\[#[0-9a-fA-F]+\]/g, 'bg-surface-1');
  content = content.replace(/bg-white dark:bg-white\/5/g, 'bg-surface-1');
  content = content.replace(/bg-white dark:bg-gray-\d+/g, 'bg-surface-1');
  content = content.replace(/border-gray-\d+\s+dark:border-\[#[0-9a-fA-F]+\]/g, 'border-hairline');
  content = content.replace(/border-gray-\d+\s+dark:border-white\/10/g, 'border-hairline');
  content = content.replace(/border-gray-\d+\s+dark:border-gray-\d+/g, 'border-hairline');
  content = content.replace(/dark:bg-white\/\d+/g, 'bg-surface-1');
  
  // Text colors
  content = content.replace(/text-gray-900 dark:text-white/g, 'text-ink');
  content = content.replace(/text-gray-800 dark:text-gray-100/g, 'text-ink');
  content = content.replace(/text-gray-700 dark:text-gray-200/g, 'text-ink');
  content = content.replace(/text-gray-700 dark:text-gray-300/g, 'text-ink-muted');
  content = content.replace(/text-gray-600 dark:text-white\/60/g, 'text-ink-subtle');
  content = content.replace(/text-gray-600 dark:text-gray-400/g, 'text-ink-subtle');
  content = content.replace(/text-gray-500 dark:text-gray-400/g, 'text-ink-subtle');
  content = content.replace(/text-gray-500 dark:text-gray-500/g, 'text-ink-tertiary');

  // Hover
  content = content.replace(/hover:bg-gray-50 dark:hover:bg-white\/5/g, 'hover:bg-surface-2');
  content = content.replace(/hover:bg-gray-100 dark:hover:bg-gray-800/g, 'hover:bg-surface-2');
  content = content.replace(/hover:text-gray-900 dark:hover:text-white/g, 'hover:text-ink');
  
  // Shadows
  content = content.replace(/\bshadow-sm\b/g, '');
  content = content.replace(/\bshadow-md\b/g, '');
  content = content.replace(/\bshadow-lg\b/g, '');
  content = content.replace(/\bshadow\b/g, '');
  
  // Specific Panel spacing (e.g. gaps between sections)
  content = content.replace(/gap-8/g, 'gap-[96px]'); // Make major section gaps 96px as requested

  // Clean up double spaces from replacements
  content = content.replace(/  +/g, ' ');

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Pages upgraded successfully.');
