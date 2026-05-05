const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Find and replace all dark classes that contain gray, zinc, #, white
  content = content.replace(/\bdark:[^\s"']*(gray|zinc|#|white)[^\s"']*\b/g, '');

  // specific typo fix
  content = content.replace(/\bdark:surface-1\b/g, '');

  // clean up leftover duplicate spaces
  content = content.replace(/className="([^"]+)"/g, (match, p1) => {
    return 'className="' + p1.replace(/\s+/g, ' ').trim() + '"';
  });

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Round 4 complete.');
