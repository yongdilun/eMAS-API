const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Fix typos
  content = content.replace(/dark:border-t-\[#[0-9a-fA-F]+\]/g, '');
  content = content.replace(/dark:surface-1/g, '');
  content = content.replace(/bg-surface-10\/20/g, 'bg-surface-1');

  // Also clean up any double spaces in classNames
  content = content.replace(/className="([^"]+)"/g, (match, p1) => {
    return 'className="' + p1.replace(/\s+/g, ' ').trim() + '"';
  });

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Round 5 complete.');
