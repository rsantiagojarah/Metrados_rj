import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, unlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, spawnSync } from 'node:child_process';

const adapter = fileURLToPath(new URL('../session-memory-adapter.mjs', import.meta.url));

test('memory hook handles 900 dirty files within its existing 5 second budget', () => {
  const prefix = join(tmpdir(), 'metrado-hook-test-');
  const root = mkdtempSync(prefix);
  const git = (...args) => execFileSync('git', args, {
    cwd: root, encoding: 'utf8', windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
  function hook(event) {
    const started = performance.now();
    const child = spawnSync(process.execPath, [adapter, 'codex', event], {
      cwd: root, input: JSON.stringify({ cwd: root, session_id: 'performance-regression' }),
      encoding: 'utf8', timeout: 5000, windowsHide: true,
    });
    assert.equal(child.error, undefined, 'hook must finish before 5 seconds: ' + child.error?.code);
    assert.equal(child.status, 0, child.stderr);
    assert.doesNotThrow(() => JSON.parse(child.stdout));
    console.log(event + ': ' + Math.round(performance.now() - started) + ' ms');
  }
  try {
    git('init', '-q');
    mkdirSync(join(root, '.rsc'));
    writeFileSync(join(root, '.rsc.json'), '{"memory":{"enabled":true}}');
    for (let i = 0; i < 900; i++) writeFileSync(join(root, 'file-' + i + '.txt'), 'content ' + i);
    const special = ['espacio ñ.txt', '-leading.txt', 'empty.txt', 'binary.dat'];
    writeFileSync(join(root, special[0]), 'texto con acentos');
    writeFileSync(join(root, special[1]), 'leading dash');
    writeFileSync(join(root, special[2]), '');
    writeFileSync(join(root, special[3]), Buffer.from([0, 1, 255, 13, 10]));
    writeFileSync(join(root, 'removed.txt'), 'deleted');
    git('add', '--', 'removed.txt');
    unlinkSync(join(root, 'removed.txt'));
    hook('request');
    const anchorPath = join(root, '.rsc', 'memory', 'anchors', 'codex--performance-regression.json');
    const anchor = JSON.parse(readFileSync(anchorPath, 'utf8'));
    for (const name of special) {
      assert.equal(anchor.baselineFingerprints[name], git('hash-object', '--no-filters', '--', name), name);
    }
    assert.equal(anchor.baselineFingerprints['removed.txt'], null);
    writeFileSync(join(root, 'file-0.txt'), 'changed');
    hook('edit');
    const record = JSON.parse(readFileSync(join(root, '.rsc', 'memory', 'sessions', 'codex--performance-regression.json'), 'utf8'));
    assert.equal(record.editCount, 1);
    const updated = JSON.parse(readFileSync(anchorPath, 'utf8'));
    assert.equal(updated.lastFingerprints['file-0.txt'], git('hash-object', '--no-filters', '--', 'file-0.txt'));
    hook('turn');
    const unchanged = JSON.parse(readFileSync(join(root, '.rsc', 'memory', 'sessions', 'codex--performance-regression.json'), 'utf8'));
    assert.equal(unchanged.editCount, 1, 'unchanged files must not count as edits');
  } finally {
    // Delete only this test's generated directory, never a project or a broad temp root.
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(resolve(root).startsWith(resolve(prefix)));
    rmSync(root, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  }
});
