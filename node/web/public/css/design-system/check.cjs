#!/usr/bin/env node
// Sprawdza kopię design systemu w projekcie. Kopiowany przez shared/design-system/sync.js, nie edytuj.
// 1. Pliki kopii są takie, jakie zapisał sync (nikt ich nie zmienił ręcznie). Działa też w CI.
// 2. Gdy obok projektu jest źródło (../shared), kopia jest z nim zgodna.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const sha = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const lock = JSON.parse(fs.readFileSync(path.join(__dirname, 'design-system.lock.json'), 'utf8'));
const errors = [];

const edited = Object.entries(lock.files)
  .filter(([file, hash]) => !fs.existsSync(path.join(__dirname, file)) || sha(path.join(__dirname, file)) !== hash)
  .map(([file]) => file);
if (edited.length > 0) {
  errors.push(
    `Kopia zmieniona poza sync: ${edited.join(', ')}. Zmień źródło w shared/design-system i uruchom npm run sync-design-system.`,
  );
}

const source = path.resolve(__dirname, lock.source);
if (fs.existsSync(path.join(source, 'sync.js'))) {
  const sourceVersion = JSON.parse(fs.readFileSync(path.join(source, 'tokens.json'), 'utf8')).meta.version;
  const stale = Object.entries(lock.files)
    .filter(([file, hash]) => !fs.existsSync(path.join(source, file)) || sha(path.join(source, file)) !== hash)
    .map(([file]) => file);
  if (stale.length > 0) {
    const hint = sourceVersion === lock.version ? ' Źródło zmieniono bez podbicia meta.version w tokens.json.' : '';
    errors.push(
      `Kopia ${lock.version} jest nieaktualna względem źródła ${sourceVersion}: ${stale.join(', ')}. Uruchom npm run sync-design-system.${hint}`,
    );
  }
} else {
  console.log('Źródło design systemu niedostępne (np. w CI): sprawdzono tylko integralność kopii.');
}

if (errors.length > 0) {
  for (const error of errors) console.error(`✗ ${error}`);
  process.exit(1);
}
console.log(`Design system ${lock.version}: kopia zgodna`);
