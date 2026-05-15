const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Surface mappings
  content = content.replace(/bg-gray-100 dark:bg-\[#27363a\]/g, 'bg-surface-1');
  content = content.replace(/hover:bg-gray-200 dark:hover:bg-\[#394f56\]/g, 'hover:bg-surface-2');
  content = content.replace(/bg-gray-50 dark:bg-gray-800\/50/g, 'bg-surface-1');
  content = content.replace(/hover:bg-gray-50 dark:hover:bg-gray-800/g, 'hover:bg-surface-2');
  content = content.replace(/bg-gray-100 dark:bg-gray-800/g, 'bg-surface-1');
  content = content.replace(/bg-gray-50\/50 dark:bg-gray-900\/20/g, 'bg-surface-1');
  content = content.replace(/hover:bg-gray-100 dark:hover:bg-gray-700/g, 'hover:bg-surface-2');
  content = content.replace(/bg-gray-50 dark:bg-[#101718]/g, 'bg-surface-1');

  // Specific placeholder mappings
  content = content.replace(/placeholder-gray-400 dark:placeholder-gray-500/g, 'placeholder-ink-subtle');
  content = content.replace(/placeholder-gray-500 dark:placeholder-gray-400/g, 'placeholder-ink-subtle');

  // Specific text mappings
  content = content.replace(/hover:text-gray-700 dark:hover:text-gray-300/g, 'hover:text-ink');
  content = content.replace(/text-gray-900 dark:text-gray-100/g, 'text-ink');

  // Clean up
  content = content.replace(/  +/g, ' ').replace(/className=" /g, 'className="');

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Round 2 complete.');
