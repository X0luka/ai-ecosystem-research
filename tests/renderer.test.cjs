const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const assert = require('node:assert/strict');

const source = path.resolve(__dirname, '../skills/ai-ecosystem-research');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-research-renderer-'));
fs.cpSync(source, path.join(temp, 'moved skill'), {recursive: true});
const renderer = path.join(temp, 'moved skill/scripts/render-report.cjs');
const input = path.join(temp, 'report.md');
const markdown = '# Demo\n\n## Comparison\n\n| Project | Fact | Analysis |\n|---|---|---|\n| A | <!-- claim:C1 -->version<!-- /claim:C1 --> | review |\n\n<!-- claim:C2 -->\nDocumented paragraph.\n<!-- /claim:C2 -->\n\n<script>alert(1)</script>\n\n[unsafe](javascript:alert%281%29)\n\n[line](notes.md#detail)\n\nText<br>next';
fs.writeFileSync(input, markdown);
for (const theme of ['dark', 'light']) {
  const output = path.join(temp, 'output', theme + '.html');
  cp.execFileSync(process.execPath, [renderer, '--input', input, '--output', output, '--theme', theme, '--title', 'Demo <test>'], {cwd: os.tmpdir()});
  const html = fs.readFileSync(output, 'utf8');
  assert(html.includes('data-theme="' + theme + '"'));
  assert(html.includes('<title>Demo &lt;test&gt;</title>'));
  assert(html.includes('<table>'));
  assert(html.includes('<td>version</td>'));
  assert(html.includes('<p>Documented paragraph.</p>'));
  assert(!html.includes('claim:C'));
  assert(html.includes('<br>'));
  assert(html.includes('href="../notes.md#detail"'));
  assert(!html.includes('<script>alert'));
  assert(!html.includes('href="javascript:'));
  assert.equal(fs.readFileSync(input, 'utf8'), markdown);
}
const email = path.join(temp, 'email.html');
cp.execFileSync(process.execPath, [path.join(temp, 'moved skill/scripts/render-email.cjs'), input, email]);
const emailHtml = fs.readFileSync(email, 'utf8');
assert(emailHtml.includes('Documented paragraph.'));
assert(emailHtml.includes('>version</td>'));
assert(!emailHtml.includes('claim:C'));
assert(!emailHtml.includes('<script>alert'));
assert.notEqual(cp.spawnSync(process.execPath, [renderer, '--input', input, '--output', input]).status, 0);
assert.notEqual(cp.spawnSync(process.execPath, [renderer, '--input', input, '--output', path.join(temp, 'bad.html'), '--theme', 'invalid']).status, 0);
const code = fs.readFileSync(renderer, 'utf8');
for (const line of code.split('\n').filter(line => line.startsWith('html[data-theme="dark"]'))) {
  for (const color of line.match(/#[a-f0-9]{6}/gi) || []) {
    assert(color.slice(1,3) === color.slice(3,5) && color.slice(3,5) === color.slice(5,7), 'Non-neutral dark color: ' + color);
  }
}
console.log('PASS: relocation, both themes, escaping, relative links, input preservation and gray palette.');
console.log('Temporary test outputs: ' + temp);
