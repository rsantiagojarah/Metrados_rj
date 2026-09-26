import assert from 'node:assert/strict';
import { test } from 'node:test';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

test('capture and resume request hidden windows for every Git child', async () => {
  const prefix = join(tmpdir(), 'metrado-hidden-hook-test-');
  const root = mkdtempSync(prefix);
  const original = childProcess.execFileSync;
  const calls = [];
  try {
    original('git', ['init', '-q'], { cwd: root, windowsHide: true });
    writeFileSync(join(root, 'sample.txt'), 'baseline');
    childProcess.execFileSync = (file, args, options = {}) => {
      calls.push({ file, args, windowsHide: options.windowsHide });
      // Record the real options, but never reproduce visible popups on the user's desktop.
      return original(file, args, { ...options, windowsHide: true });
    };
    syncBuiltinESMExports();
    const { capture, resume } = await import('../session-memory-core.mjs');
    const input = { cwd: root, sessionId: 'hidden-test', target: 'codex', force: true };
    assert.ok(capture({ ...input, event: 'request' }).record);
    writeFileSync(join(root, 'sample.txt'), 'edited');
    assert.equal(capture({ ...input, event: 'edit' }).record.editCount, 1);
    assert.ok(resume(input).record);
    assert.ok(calls.some(call => call.args.includes('hash-object')), 'exercise batch hashing');
    assert.ok(calls.some(call => call.args.includes('rev-parse')), 'exercise shared Git helper');
    const visible = calls.filter(call => call.windowsHide !== true);
    assert.deepEqual(visible, [], 'all child processes must explicitly request hidden windows');
    console.log('Verified ' + calls.length + ' hidden Git launches across capture and resume');
  } finally {
    childProcess.execFileSync = original;
    syncBuiltinESMExports();
    assert.equal(dirname(resolve(root)), resolve(tmpdir()));
    assert.ok(resolve(root).startsWith(resolve(prefix)));
    rmSync(root, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  }
});
