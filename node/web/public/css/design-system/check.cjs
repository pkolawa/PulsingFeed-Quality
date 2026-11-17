#!/usr/bin/env node
// Sprawdza kopię design systemu w projekcie. Kopiowany przez shared/design-system/sync.js, nie edytuj.
// 1. Pliki kopii są takie, jakie zapisał sync, i nie ma plików spoza niego. Działa też w CI.
// 2. Kopia nie pochodzi z niezacommitowanych zmian w shared.
// 3. Gdy obok projektu jest źródło (../shared), kopia jest z nim zgodna. Źródło starsze od kopii
//    daje tylko ostrzeżenie: to shared trzeba zaktualizować, a nie kopię.
// sync.js korzysta z funkcji tego pliku, więc obie strony liczą skróty i porównują wersje tak samo.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LOCK = 'design-system.lock.json';

// Skrót z ujednoliconymi końcami linii: checkout z core.autocrlf nie zmienia wyniku.
const sha = (content) =>
  crypto.createHash('sha256').update(content.toString('utf8').replace(/\r\n/g, '\n')).digest('hex');
const hashFile = (file) => (fs.existsSync(file) ? sha(fs.readFileSync(file)) : null);

// Zawartość pliku JSON albo null, gdy go nie ma lub jest uszkodzony.
const readJson = (file) => {
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
};
const versionOf = (dir) => readJson(path.join(dir, 'tokens.json'))?.meta?.version ?? null;

// Porównanie wersji X.Y.Z: liczba ujemna, zero albo dodatnia; null, gdy któraś nie ma tej postaci.
const compareVersions = (a, b) => {
  const parse = (version) => /^(\d+)\.(\d+)\.(\d+)$/.exec(version ?? '')?.slice(1).map(Number);
  const [x, y] = [parse(a), parse(b)];
  if (!x || !y) return null;
  return x.map((part, i) => part - y[i]).find((diff) => diff !== 0) ?? 0;
};

// Pliki, których skrót w katalogu dir nie zgadza się z oczekiwanym (brak pliku też się liczy).
const mismatched = (dir, expected) =>
  Object.entries(expected)
    .filter(([file, hash]) => hashFile(path.join(dir, file)) !== hash)
    .map(([file]) => file);

function check(dir) {
  const errors = [];
  const warnings = [];
  const lock = readJson(path.join(dir, LOCK));
  if (!lock?.files) {
    return { errors: [`Brak lub uszkodzony ${LOCK}. Uruchom npm run sync-design-system.`], warnings };
  }
  const version = versionOf(dir);

  const edited = mismatched(dir, lock.files);
  if (edited.length > 0) {
    errors.push(
      `Kopia zmieniona poza sync: ${edited.join(', ')}. Zmień źródło w shared/design-system i uruchom npm run sync-design-system.`,
    );
  }
  // Pliki ukryte (np. .DS_Store) pomijane.
  const extra = fs.readdirSync(dir).filter((file) => !file.startsWith('.') && file !== LOCK && !(file in lock.files));
  if (extra.length > 0) {
    errors.push(`Pliki spoza sync: ${extra.join(', ')}. Usuń je albo dodaj do shared/design-system/copied-files.json.`);
  }
  if (lock.unreleased) {
    errors.push(
      'Kopia pochodzi z niezacommitowanych zmian w shared/design-system. Zacommituj shared (z podbiciem meta.version) i uruchom npm run sync-design-system.',
    );
  }

  const source = path.resolve(dir, lock.source ?? '');
  const sourceAvailable = fs.existsSync(path.join(source, 'sync.js'));
  if (sourceAvailable) {
    const sourceFiles = readJson(path.join(source, 'copied-files.json')) ?? Object.keys(lock.files);
    const expected = Object.fromEntries(sourceFiles.map((file) => [file, hashFile(path.join(source, file))]));
    // Plik dodany w źródle albo usunięty z locka też czyni kopię nieaktualną.
    const stale = [...new Set([...Object.keys(lock.files), ...sourceFiles])].filter(
      (file) => lock.files[file] !== expected[file],
    );
    if (stale.length > 0) {
      const sourceVersion = versionOf(source);
      const order = compareVersions(sourceVersion, version);
      if (order !== null && order < 0) {
        warnings.push(
          `Źródło ${sourceVersion} w ../shared jest starsze niż kopia ${version}. Zaktualizuj shared; sync nie cofnie kopii bez --force.`,
        );
      } else {
        // Podpowiedź tylko wtedy, gdy kopia zgadza się z lockiem, czyli różnica jest po stronie źródła.
        const sourceChanged = stale.every((file) => file in lock.files && !edited.includes(file));
        const hint = order === 0 && sourceChanged ? ' Źródło zmieniono bez podbicia meta.version w tokens.json.' : '';
        errors.push(
          `Kopia ${version ?? '?'} jest nieaktualna względem źródła ${sourceVersion ?? '(nieczytelny tokens.json)'}: ${stale.join(', ')}. Uruchom npm run sync-design-system.${hint}`,
        );
      }
    }
  }
  return { errors, warnings, version, sourceAvailable };
}

if (require.main === module) {
  const { errors, warnings, version, sourceAvailable } = check(__dirname);
  if (sourceAvailable === false) {
    console.log('Źródło design systemu niedostępne (np. w CI): sprawdzono tylko integralność kopii.');
  }
  for (const warning of warnings) console.warn(`! ${warning}`);
  if (errors.length > 0) {
    for (const error of errors) console.error(`✗ ${error}`);
    process.exit(1);
  }
  console.log(`Design system ${version}: kopia zgodna`);
}

module.exports = { LOCK, sha, readJson, versionOf, compareVersions };
