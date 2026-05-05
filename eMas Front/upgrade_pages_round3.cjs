const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Strip dark variants for non-semantic colors
  content = content.replace(/dark:bg-gray-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:bg-zinc-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:bg-\[#[0-9a-fA-F]+\]/g, '');
  content = content.replace(/dark:border-gray-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:border-zinc-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:border-\[#[0-9a-fA-F]+\]/g, '');
  content = content.replace(/dark:text-white/g, '');
  content = content.replace(/dark:text-gray-\d+/g, '');
  content = content.replace(/dark:text-\[#[0-9a-fA-F]+\]/g, '');

  content = content.replace(/dark:hover:bg-gray-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:hover:bg-zinc-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:hover:bg-\[#[0-9a-fA-F]+\]/g, '');
  content = content.replace(/dark:hover:border-gray-\d+(?:\/\d+)?/g, '');
  content = content.replace(/dark:hover:text-white/g, '');
  content = content.replace(/dark:hover:text-gray-\d+/g, '');

  // Strip non-semantic background and borders to their respective semantic variables
  content = content.replace(/bg-gray-50\/50/g, 'bg-surface-1');
  content = content.replace(/bg-gray-50/g, 'bg-surface-1');
  content = content.replace(/bg-gray-100/g, 'bg-surface-1');
  content = content.replace(/bg-gray-200/g, 'bg-surface-1');
  content = content.replace(/bg-gray-800/g, 'bg-surface-1');
  content = content.replace(/bg-gray-900/g, 'bg-surface-1');
  content = content.replace(/bg-zinc-200/g, 'bg-surface-1');

  content = content.replace(/hover:bg-gray-50/g, 'hover:bg-surface-2');
  content = content.replace(/hover:bg-gray-100/g, 'hover:bg-surface-2');
  content = content.replace(/hover:bg-gray-200/g, 'hover:bg-surface-2');
  content = content.replace(/hover:bg-gray-300/g, 'hover:bg-surface-2');

  content = content.replace(/border-gray-200/g, 'border-hairline');
  content = content.replace(/border-gray-300/g, 'border-hairline');
  content = content.replace(/border-zinc-200/g, 'border-hairline');
  content = content.replace(/border-t-gray-200/g, 'border-t-hairline');

  content = content.replace(/text-gray-900/g, 'text-ink');
  content = content.replace(/text-gray-800/g, 'text-ink');
  content = content.replace(/text-zinc-900/g, 'text-ink');
  content = content.replace(/text-gray-700/g, 'text-ink-muted');
  content = content.replace(/text-gray-600/g, 'text-ink-subtle');
  content = content.replace(/text-zinc-500/g, 'text-ink-subtle');
  content = content.replace(/text-gray-500/g, 'text-ink-subtle');
  content = content.replace(/text-gray-400/g, 'text-ink-tertiary');
  content = content.replace(/text-gray-300/g, 'text-ink-tertiary');

  // Clean up duplicate spaces inside classNames
  content = content.replace(/className="([^"]+)"/g, (match, p1) => {
    return 'className="' + p1.replace(/\s+/g, ' ').trim() + '"';
  });

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Round 3 cleanup complete.');
