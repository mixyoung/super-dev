import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { apply, decodeSnapshot } from '../index.js';

function definition(get = () => assert.fail('unbound calls must not inspect a directory'), config) {
  const registered = [];
  apply({ tools: { register: item => registered.push(item) }, workingDirectory: { get } }, config);
  assert.deepEqual(registered.map(item => item.name), ['super_dev_status']);
  return registered[0];
}

const valid = () => ({
  schema: 1, outcome: 'observed', reason: '',
  checks: { standard: 'valid', seeai: 'modified', rules: 'valid' },
  workflow: { state: 'recorded', flow: 'standard', stage: 'docs_confirm', work_item: '测试-work', revision: 2, next: 'review_documents' },
});

test('tool refuses a path argument without using the directory service', async () => {
  const result = await definition().execute({ path: 'unrelated-project' }, {});
  assert.equal(result.reason, 'arguments');
});

test('tool requires an explicit project bound to an existing agent session', async () => {
  const tool = definition();
  assert.equal((await tool.execute({}, {})).reason, 'workspace');
  assert.equal((await tool.execute({}, { agent: { session: { header: {} } } })).reason, 'workspace');
  const controller = new AbortController();
  controller.abort();
  assert.equal((await tool.execute({}, { signal: controller.signal })).reason, 'cancelled');
});

test('an enabled bundle with no trusted Python configuration does not search for one', async () => {
  const root = fileURLToPath(new URL('..', import.meta.url));
  const tool = definition(() => root);
  const result = await tool.execute({}, { agent: { session: { header: { cwd: root } } } });
  assert.equal(result.reason, 'bridge_unavailable');
});

test('only approved fields are visible in canonical value and rendered text', () => {
  const input = valid();
  input.raw_credential = 'OWNED_NOT_FOR_OUTPUT';
  input.workflow.assistant_prompt = 'OWNED_NOT_FOR_OUTPUT';
  input.checks.unrelated_file = 'OWNED_NOT_FOR_OUTPUT';
  const clean = decodeSnapshot(JSON.stringify(input));
  assert.deepEqual(clean, valid());
  const output = definition().output.render({}, clean).map(x => x.text).join('\n');
  assert.match(output, /文档确认/);
  assert.match(output, /\/super-dev-seeai：内容不符（FAIL）/);
  assert.match(output, /不代表规则已进入会话/);
  assert.doesNotMatch(output, /OWNED_NOT_FOR_OUTPUT/);
});

test('unknown, invalid or inconsistent Core data is refused', () => {
  for (const mutation of [
    x => x.schema = 7,
    x => x.workflow.work_item = '../../not-a-work-item',
    x => x.workflow.stage = 'start_shell',
    x => x.workflow.next = ['/approve'],
    x => x.workflow.state = 'invalid',
    x => x.checks.seeai = ['valid'],
  ]) {
    const input = valid();
    mutation(input);
    assert.throws(() => decodeSnapshot(JSON.stringify(input)));
  }
});
