import { execFile } from 'node:child_process';
import { realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

export const inject = ['tools', 'workingDirectory'];
const run = promisify(execFile);
const MODULE = 'super_dev.integrations.dsh_plugin_snapshot';
const NAMES = ['standard', 'seeai', 'rules'];
const CHECKS = {
  valid: '通过（PASS）', missing: '缺失（FAIL）', modified: '内容不符（FAIL）',
  unreadable: '无法安全读取（BLOCKED）', unchecked: '未检查',
};
const REASONS = {
  workspace: '没有已绑定的本地项目，或当前目录不在该项目内。',
  not_setup: '当前项目未发现可核对的 Super Dev 接入或任务记录。',
  bridge_unavailable: '尚未配置项目之外的可信 Super Dev Python，或该解释器不可用。',
  bridge_failed: '只读查询失败或超时；请核对同版 Super Dev 核心。',
  cancelled: '本次查询已取消。',
  arguments: '这个工具不接受路径、命令或其他参数。',
};
const STAGES = {
  baseline: '基线核对', research: '调研', docs: '三份核心文档', docs_confirm: '文档确认',
  spec: '执行规格', frontend: '前端', preview_confirm: '预览确认', backend: '后端与测试',
  quality: '质量检查', delivery: '交付', build_fullstack: '全栈实现', polish: '收尾优化',
};
const HINTS = {
  review_documents: '请先核对当前任务的三份核心文档，确认由你本人作出。',
  review_preview: '请先核对当前任务的预览，确认由你本人作出。',
  continue_existing: '如需续跑，请在原会话说「继续当前流程」，由现有核心重新判定。',
};
const TEXT = { type: 'string' };
const CLOSED = properties => ({ type: 'object', properties, required: Object.keys(properties), additionalProperties: false });
const SCHEMA = CLOSED({
  schema: { type: 'integer' }, outcome: TEXT, reason: TEXT,
  checks: CLOSED({ standard: TEXT, seeai: TEXT, rules: TEXT }),
  workflow: CLOSED({ state: TEXT, flow: TEXT, stage: TEXT, work_item: TEXT, revision: { type: 'integer' }, next: TEXT }),
});

function denied(reason) {
  return {
    schema: 1, outcome: 'blocked', reason,
    checks: { standard: 'unchecked', seeai: 'unchecked', rules: 'unchecked' },
    workflow: { state: 'unchecked', flow: '', stage: '', work_item: '', revision: 0, next: '' },
  };
}

function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function localAbsolute(value) {
  return typeof value === 'string' && !value.includes('\0') && path.isAbsolute(value)
    && !value.split(process.platform === 'win32' ? /[\\/]/ : '/').includes('..')
    && (process.platform !== 'win32' || /^[A-Za-z]:[\\/]/.test(value));
}

function inside(root, value) {
  const relative = path.relative(root, value);
  return relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

async function plainPath(value) {
  if (!localAbsolute(value)) return null;
  const resolved = await realpath(value);
  return path.relative(resolved, value) === '' ? resolved : null;
}

async function workspace(ctx, execution) {
  const session = execution?.agent?.session;
  const original = session?.header?.cwd;
  if (!localAbsolute(original)) return null;
  const root = await plainPath(original);
  if (!root || root === path.parse(root).root || !(await stat(root)).isDirectory()) return null;
  // Unlike ensure(), get() only observes the directory projection. The explicit
  // header above prevents the service's default directory from granting access.
  const current = ctx.workingDirectory.get(session);
  if (!localAbsolute(current) || !inside(root, current)) return null;
  const resolved = await plainPath(current);
  return resolved && inside(root, resolved) && (await stat(resolved)).isDirectory() ? root : null;
}

function namedOption(options, value) {
  return typeof value === 'string' && Object.hasOwn(options, value);
}

export function decodeSnapshot(text) {
  const value = JSON.parse(text);
  if (!object(value) || value.schema !== 1 || !object(value.checks) || !object(value.workflow)) {
    throw new Error('unsupported snapshot');
  }
  const { checks, workflow } = value;
  if (!['observed', 'blocked'].includes(value.outcome)
      || (value.outcome === 'observed' ? value.reason !== '' : !['workspace', 'not_setup'].includes(value.reason))
      || NAMES.some(name => !namedOption(CHECKS, checks[name]))
      || !['recorded', 'not_started', 'invalid', 'unchecked'].includes(workflow.state)
      || !['', 'standard', 'seeai'].includes(workflow.flow)
      || !(workflow.stage === '' || namedOption(STAGES, workflow.stage))
      || !(workflow.next === '' || namedOption(HINTS, workflow.next))
      || typeof workflow.work_item !== 'string'
      || !/^(?:[\p{L}\p{N}](?:[\p{L}\p{N}_.-]{0,126}[\p{L}\p{N}])?)?$/u.test(workflow.work_item)
      || !Number.isSafeInteger(workflow.revision) || workflow.revision < 0) {
    throw new Error('invalid snapshot values');
  }
  const recorded = workflow.state === 'recorded';
  if (recorded ? (!workflow.flow || !workflow.stage || !workflow.work_item || !workflow.revision)
    : (workflow.flow || workflow.stage || workflow.work_item || workflow.revision || workflow.next)) {
    throw new Error('inconsistent workflow snapshot');
  }
  // Never expose arbitrary data from a subprocess, even if the Core changes.
  return {
    schema: 1, outcome: value.outcome, reason: value.reason,
    checks: Object.fromEntries(NAMES.map(name => [name, checks[name]])),
    workflow: {
      state: workflow.state, flow: workflow.flow, stage: workflow.stage,
      work_item: workflow.work_item, revision: workflow.revision, next: workflow.next,
    },
  };
}

function render(value) {
  const lines = ['Super Dev 项目检查（只读）'];
  if (value.outcome === 'blocked') lines.push(`受阻（BLOCKED）：${REASONS[value.reason]}`);
  if (NAMES.some(name => value.checks[name] !== 'unchecked')) {
    lines.push(`标准入口 /super-dev：${CHECKS[value.checks.standard]}`,
      `赛事入口 /super-dev-seeai：${CHECKS[value.checks.seeai]}`,
      `DSH 项目规则：${CHECKS[value.checks.rules]}`);
  }
  const task = value.workflow;
  if (task.state === 'recorded') {
    lines.push(`工作项：${task.work_item}｜${task.flow === 'seeai' ? 'SEEAI' : '标准'}｜${STAGES[task.stage]}`);
    if (task.next) lines.push(HINTS[task.next]);
  } else if (task.state === 'not_started') {
    lines.push('当前项目没有已记录的工作项。');
  } else if (task.state === 'invalid') {
    lines.push('当前任务状态不可核验（BLOCKED）。没有使用历史快照或替你继续。');
  }
  lines.push('只检查项目文件和已落盘任务；不代表规则已进入会话、技能来源已受保护或桌面流程已验收。');
  return [{ type: 'text', text: lines.join('\n') }];
}

function workerEnvironment() {
  const keys = new Set(['SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE']);
  return Object.fromEntries(Object.entries(process.env).filter(([key]) => keys.has(key.toUpperCase())));
}

export function apply(ctx, config = {}) {
  const executable = config?.pythonExecutable;
  ctx.tools.register({
    name: 'super_dev_status',
    description: '只读查询当前项目的 Super Dev 双入口接入、已记录任务和确认等待状态；不推进或确认流程。',
    parameters: CLOSED({}),
    output: { schema: SCHEMA, render: (_args, value) => render(value) },
    timeoutMs: 7500,
    async execute(args, execution) {
      if (!object(args) || Object.keys(args).length) return denied('arguments');
      if (execution?.signal?.aborted) return denied('cancelled');
      let project;
      try { project = await workspace(ctx, execution); } catch { return denied('workspace'); }
      if (!project) return denied('workspace');
      let python;
      try {
        python = await plainPath(executable);
        if (!python || inside(project, python) || !(await stat(python)).isFile()
          || (process.platform === 'win32' && path.extname(python).toLowerCase() !== '.exe')) {
          return denied('bridge_unavailable');
        }
      } catch { return denied('bridge_unavailable'); }
      if (execution?.signal?.aborted) return denied('cancelled');
      try {
        const { stdout, stderr } = await run(python, ['-I', '-B', '-m', MODULE, project], {
          cwd: path.dirname(python), env: workerEnvironment(), shell: false, windowsHide: true,
          timeout: 6500, maxBuffer: 32768, encoding: 'utf8', signal: execution?.signal,
        });
        if (execution?.signal?.aborted) return denied('cancelled');
        if (stderr.trim()) return denied('bridge_failed');
        return decodeSnapshot(stdout);
      } catch {
        return denied(execution?.signal?.aborted ? 'cancelled' : 'bridge_failed');
      }
    },
  });
}
