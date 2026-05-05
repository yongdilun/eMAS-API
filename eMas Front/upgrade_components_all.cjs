const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Get all tracked files in src/
const allFiles = execSync('git ls-files "src/"', { encoding: 'utf-8' }).split('\n').filter(f => f.endsWith('.jsx'));

// Get all modified files
const modifiedFiles = execSync('git diff --name-only', { encoding: 'utf-8' }).split('\n').filter(Boolean);

// We want files that are in allFiles but NOT in modifiedFiles
const filesToProcess = allFiles.filter(f => !modifiedFiles.includes(f));

console.log(`Found ${filesToProcess.length} unmodified JSX files to process.`);

filesToProcess.forEach(file => {
  const filepath = path.join(process.cwd(), file);
  if (!fs.existsSync(filepath)) return;
  
  let content = fs.readFileSync(filepath, 'utf8');
  let originalContent = content;

  // Backgrounds
  content = content.replace(/bg-white\s+dark:bg-\[[^\]]+\]/g, 'bg-surface-1');
  content = content.replace(/bg-white\s+dark:bg-gray-\d+/g, 'bg-surface-1');
  content = content.replace(/bg-white\s+dark:bg-white\/\d+/g, 'bg-surface-1');
  content = content.replace(/bg-gray-50\s+dark:bg-gray-\d+\/?\d*/g, 'bg-surface-2');
  content = content.replace(/bg-gray-100\s+dark:bg-gray-\d+\/?\d*/g, 'bg-surface-2');
  content = content.replace(/bg-gray-800\s+dark:bg-gray-900/g, 'bg-surface-3');
  
  // Standalone backgrounds (if dark prefix wasn't strictly paired)
  content = content.replace(/\bbg-white\b(?!\s*\/)/g, 'bg-surface-1');
  content = content.replace(/\bdark:bg-gray-800\b/g, '');
  content = content.replace(/\bdark:bg-gray-900\b/g, '');
  content = content.replace(/\bbg-gray-50\b/g, 'bg-surface-2');
  content = content.replace(/\bbg-gray-100\b/g, 'bg-surface-2');
  
  // Borders
  content = content.replace(/border-gray-\d+\s+dark:border-\[[^\]]+\]/g, 'border-hairline');
  content = content.replace(/border-gray-\d+\s+dark:border-gray-\d+/g, 'border-hairline');
  content = content.replace(/border-gray-\d+\s+dark:border-white\/\d+/g, 'border-hairline');
  content = content.replace(/\bborder-gray-200\b/g, 'border-hairline');
  content = content.replace(/\bdark:border-gray-700\b/g, '');
  content = content.replace(/\bdark:border-gray-800\b/g, '');
  content = content.replace(/\bdark:border-white\/\d+\b/g, '');

  // Text
  content = content.replace(/text-gray-900\s+dark:text-white/g, 'text-ink');
  content = content.replace(/text-gray-800\s+dark:text-gray-100/g, 'text-ink');
  content = content.replace(/text-gray-700\s+dark:text-gray-200/g, 'text-ink');
  content = content.replace(/text-gray-700\s+dark:text-gray-300/g, 'text-ink-muted');
  content = content.replace(/text-gray-600\s+dark:text-white\/\d+/g, 'text-ink-subtle');
  content = content.replace(/text-gray-600\s+dark:text-gray-400/g, 'text-ink-subtle');
  content = content.replace(/text-gray-500\s+dark:text-gray-400/g, 'text-ink-subtle');
  content = content.replace(/text-gray-500\s+dark:text-gray-500/g, 'text-ink-tertiary');
  
  // Standalone text
  content = content.replace(/\btext-gray-900\b/g, 'text-ink');
  content = content.replace(/\btext-gray-800\b/g, 'text-ink');
  content = content.replace(/\btext-gray-700\b/g, 'text-ink-muted');
  content = content.replace(/\btext-gray-600\b/g, 'text-ink-subtle');
  content = content.replace(/\btext-gray-500\b/g, 'text-ink-subtle');
  content = content.replace(/\bdark:text-white\b/g, '');
  content = content.replace(/\bdark:text-gray-\d+\b/g, '');

  // Primary colors
  content = content.replace(/\bbg-blue-600\s+dark:bg-blue-500\b/g, 'bg-primary');
  content = content.replace(/\bbg-blue-600\b/g, 'bg-primary');
  content = content.replace(/\btext-blue-600\s+dark:text-blue-400\b/g, 'text-primary');
  content = content.replace(/\btext-blue-600\b/g, 'text-primary');
  content = content.replace(/\btext-blue-500\b/g, 'text-primary');
  content = content.replace(/\bborder-blue-600\b/g, 'border-primary');
  content = content.replace(/\bdark:bg-blue-500\b/g, '');
  content = content.replace(/\bdark:text-blue-400\b/g, '');
  content = content.replace(/\bdark:border-blue-500\b/g, '');

  // Success colors (semantic)
  content = content.replace(/\bbg-green-100\b/g, 'bg-semantic-success/20');
  content = content.replace(/\btext-green-800\b/g, 'text-semantic-success');
  content = content.replace(/\btext-green-600\b/g, 'text-semantic-success');
  content = content.replace(/\bdark:bg-green-900\/\d+\b/g, '');
  content = content.replace(/\bdark:text-green-400\b/g, '');
  
  // Red/Yellow colors to muted or subtle (Linear avoids bright accents)
  content = content.replace(/\btext-red-600\b/g, 'text-ink-muted');
  content = content.replace(/\btext-yellow-600\b/g, 'text-ink-muted');
  content = content.replace(/\bdark:text-red-400\b/g, '');
  content = content.replace(/\bdark:text-yellow-400\b/g, '');
  content = content.replace(/\bbg-red-100\b/g, 'bg-surface-2');
  content = content.replace(/\bbg-yellow-100\b/g, 'bg-surface-2');
  content = content.replace(/\bdark:bg-red-900\/\d+\b/g, '');
  content = content.replace(/\bdark:bg-yellow-900\/\d+\b/g, '');

  // Hover states
  content = content.replace(/hover:bg-gray-50\s+dark:hover:bg-white\/\d+/g, 'hover:bg-surface-2');
  content = content.replace(/hover:bg-gray-100\s+dark:hover:bg-gray-\d+/g, 'hover:bg-surface-2');
  content = content.replace(/hover:text-gray-900\s+dark:hover:text-white/g, 'hover:text-ink');
  content = content.replace(/\bhover:bg-gray-50\b/g, 'hover:bg-surface-2');
  content = content.replace(/\bhover:bg-gray-100\b/g, 'hover:bg-surface-2');
  content = content.replace(/\bdark:hover:bg-gray-\d+\b/g, '');
  content = content.replace(/\bdark:hover:bg-white\/\d+\b/g, '');
  
  // Shadows
  content = content.replace(/\bshadow-xl\b/g, '');
  content = content.replace(/\bshadow-lg\b/g, '');
  content = content.replace(/\bshadow-md\b/g, '');
  content = content.replace(/\bshadow-sm\b/g, '');
  content = content.replace(/\bshadow\b/g, '');
  
  // Rounding
  content = content.replace(/\brounded-2xl\b/g, 'rounded-xl'); // 16px is max usually
  content = content.replace(/\brounded-3xl\b/g, 'rounded-xxl');

  // Specific structural gaps
  content = content.replace(/\bgap-8\b/g, 'gap-[96px]');

  // Clean up multiple spaces
  content = content.replace(/className="([^"]+)"/g, (match, p1) => {
    return 'className="' + p1.replace(/\s+/g, ' ').trim() + '"';
  });
  
  // Handle empty classNames
  content = content.replace(/className=""/g, '');
  content = content.replace(/ \s+/g, ' ');

  if (content !== originalContent) {
    fs.writeFileSync(filepath, content, 'utf8');
    console.log(`Updated: ${file}`);
  }
});

console.log('Done upgrading remaining components.');
