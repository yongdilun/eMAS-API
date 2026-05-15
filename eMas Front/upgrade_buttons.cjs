const fs = require('fs');
const path = require('path');

const directory = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(directory).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filepath = path.join(directory, file);
  let content = fs.readFileSync(filepath, 'utf8');

  // Primary buttons
  content = content.replace(/bg-primary text-white hover:bg-primary\/90/g, 'bg-primary text-on-primary hover:bg-primary-hover');
  content = content.replace(/bg-primary text-white hover:bg-primary-hover/g, 'bg-primary text-on-primary hover:bg-primary-hover');

  // Also cleanup remaining explicit hex colors if any (like in bg-[#1b2528] that might have been missed)
  content = content.replace(/bg-\[#1b2528\]/g, 'surface-1');

  fs.writeFileSync(filepath, content, 'utf8');
});

console.log('Button and extra colors upgraded successfully.');
