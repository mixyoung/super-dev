import { execFile } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { lstat, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

export const inject = ['commands', 'workingDirectory', 'systemPrompt', 'agents', 'tools'];
const run = promisify(execFile);
const PROTOCOL = 'dsh-primary-v1';
const MODULE = 'super_dev.integrations.dsh_primary_bridge';
const OWNER = 'Super Dev 已绑定 DSH 工作项 ';
const START_UNCERTAIN = 'Core 已收到启动请求，但未核对到完整回执。';
const MODES = { 'super-dev': 'standard', 'super-dev-seeai': 'seeai' };
const ITEM = /^dsh-[0-9a-f]{20}$/;
const SESSION = /^[A-Za-z0-9_.:-]{1,128}$/;
const DIGEST = /^(?:sha256:)?[0-9a-f]{64}$/;
const CONTINUE = new Set(['继续', '继续当前流程']);
const LABELS = {
  baseline: '基线核对', research: '调研', docs: '三份核心文档', docs_confirm: '文档确认',
  spec: '执行规格', frontend: '前端', preview_confirm: '预览确认', backend: '后端与测试',
  build_fullstack: '全栈实现', polish: '收尾优化', quality: '质量检查', delivery: '交付',
};
const PROTECTED_NAMES = new Set(['.super-dev', '.dsh', '.agents', '.claude', '.codex', '.git',
  'super-dev.yaml', 'agents.md', 'agents.local.md', 'claude.md', 'claude.local.md']);
const WINDOWS_DEVICES = /^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)/i;
const deny = () => ({ kind: 'deny', reason: 'Super Dev 门禁未允许这个工具调用。' });
const error = text => ({ kind: 'error', text: `受阻（BLOCKED）：${text}` });
const success = text => ({ kind: 'success', text });

function localAbsolute(value) {
  return typeof value === 'string' && !value.includes('\0') && path.isAbsolute(value)
    && !value.split(process.platform === 'win32' ? /[\\/]/ : '/').includes('..')
    && (process.platform !== 'win32' || /^[A-Za-z]:[\\/]/.test(value));
}

function inside(root, target) {
  const rel = path.relative(root, target);
  return rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel);
}

async function plain(value) {
  if (!localAbsolute(value)) return null;
  const resolved = await realpath(value);
  return path.relative(resolved, value) === '' ? resolved : null;
}

async function workspace(ctx, agent) {
  const header = agent?.session?.header;
  if (!SESSION.test(String(agent?.id ?? '')) || header?.id !== agent.id || !localAbsolute(header.cwd)) return null;
  const root = await plain(header.cwd);
  if (!root || root === path.parse(root).root || !(await stat(root)).isDirectory()) return null;
  const cwd = ctx.workingDirectory.get(agent.session);
  if (!localAbsolute(cwd) || !inside(root, cwd)) return null;
  const current = await plain(cwd);
  return current && inside(root, current) && (await stat(current)).isDirectory() ? root : null;
}

async function fileWithin(project, cwd, value, { writing = false } = {}) {
  if (typeof value !== 'string' || !value || value.includes('\0') || value.split(/[\\/]/).includes('..')) return null;
  if (!localAbsolute(cwd) || !inside(project, cwd)) return null;
  const absolute = path.isAbsolute(value) ? value : path.join(cwd, value);
  if (!localAbsolute(absolute)) return null;
  const target = path.resolve(absolute);
  if (!inside(project, target)) return null;
  const relative = path.relative(project, target);
  if (!relative) return null;
  let cursor = project;
  for (const part of relative.split(path.sep)) {
    if (process.platform === 'win32' && (/[<>:"|?*]/.test(part) || /[. ]$/.test(part) || WINDOWS_DEVICES.test(part))) return null;
    cursor = path.join(cursor, part);
    try {
      const info = await lstat(cursor);
      if (info.isSymbolicLink() || path.relative(await realpath(cursor), cursor) !== '') return null;
      if (cursor === target && (!info.isFile() || (writing && info.nlink !== 1))) return null;
    }
    catch (err) { if (err?.code !== 'ENOENT') return null; }
  }
  return relative.split(path.sep).join('/');
}

function commandKind(raw) {
  if (!raw) return 'status';
  if (CONTINUE.has(raw)) return 'continue';
  if (/^确认(?:基线|文档|预览)(?:\s|$)/.test(raw)) return 'confirm';
  return 'start';
}

function activationFromHistory(session) {
  // Use the public command lifecycle. Experimental plugin records are not
  // available to outside plugins in this DSH version.
  const starts = new Map();
  let bound;
  let uncertain;
  for (const event of session.snapshotEvents()) {
    const data = event.data;
    if (event.type === 'command/run' && data?.source?.kind === 'user' && Object.hasOwn(MODES, data.name)) {
      const args = typeof data.args === 'string' ? data.args.trim() : '';
      starts.set(data.commandId, { mode: MODES[data.name], starting: commandKind(args) === 'start' });
    } else if (event.type === 'command/done') {
      const command = starts.get(data?.commandId);
      if (!command) continue;
      starts.delete(data.commandId);
      if (data.kind === 'success' && typeof data.text === 'string' && data.text.startsWith(OWNER)) {
        const item = data.text.slice(OWNER.length).split(/[。\s]/, 1)[0];
        if (ITEM.test(item)) bound = { mode: command.mode, item };
      } else if (command.starting && data.kind === 'error' && data.text === `受阻（BLOCKED）：${START_UNCERTAIN}`) {
        uncertain = { mode: command.mode, item: '' };
      }
    }
  }
  const pending = [...starts.values()].reverse().find(command => command.starting);
  return bound ?? (pending && { mode: pending.mode, item: '' }) ?? uncertain;
}

function message(text) {
  // Public rc.3 UserMessage shape. A user message is never a Core approval.
  return Object.freeze({ id: randomUUID(), role: 'user', source: Object.freeze({ kind: 'user' }),
    content: Object.freeze([Object.freeze({ type: 'text', text })]) });
}

export function apply(ctx, config = {}) {
  const sessions = new Map();
  const activating = new Set();
  const routerPath = config.pythonExecutable;
  if (config.allowImplementationTerminal === true) throw new Error('当前插件没有经验证的独立终端授权入口。');
  const delegated = agent => Boolean(agent?.session?.header?.parentSession);
  function scope(agent, seen = new Set()) {
    if (!agent?.session || seen.has(agent.id)) return null;
    seen.add(agent.id);
    const cached = sessions.get(agent.id);
    const history = activationFromHistory(agent.session);
    if (cached || history) return { ...history, ...cached, child: delegated(agent) };
    if (delegated(agent)) {
      const parent = ctx.agents.get(agent.session.header.parentSession);
      if (scope(parent, seen)) return { child: true };
    }
    return null;
  }

  async function core(op, root, agent, mode, item = '', digest = '', signal) {
    const python = await plain(routerPath);
    if (!python || inside(root, python) || !(await stat(python)).isFile()
        || (process.platform === 'win32' && path.extname(python).toLowerCase() !== '.exe')) {
      throw new Error('未配置项目之外的可信 Super Dev Python。');
    }
    if (signal?.aborted) throw new Error('操作已取消。');
    const envKeys = new Set(['SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE']);
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => envKeys.has(key.toUpperCase())));
    const arg = JSON.stringify({ op, project: root, session: String(agent.id), mode, item, digest });
    const { stdout, stderr } = await run(python, ['-I', '-B', '-m', MODULE, arg], {
      cwd: path.dirname(python), env, shell: false, windowsHide: true, timeout: 8500,
      maxBuffer: 512 * 1024, encoding: 'utf8', signal,
    });
    if (stderr.trim()) throw new Error('Core 查询未完成。');
    const reply = JSON.parse(stdout);
    if (reply.protocol === PROTOCOL && reply.ok === false && reply.binding === 'unowned') {
      const failure = new Error('该会话没有接管 Core 工作项。');
      failure.bindingUnowned = true;
      throw failure;
    }
    if (reply.protocol !== PROTOCOL || reply.ok !== true) throw new Error('Core 拒绝当前会话、操作或产物版本。');
    if (reply.mode !== mode || !ITEM.test(reply.item) || (item && reply.item !== item)
        || !['draft', 'wait', 'frontend', 'implement'].includes(reply.policy) || typeof reply.stage !== 'string'
        || !Array.isArray(reply.artifacts) || reply.artifacts.length > 16
        || reply.artifacts.some(name => typeof name !== 'string' || !name.startsWith(`output/${reply.item}-`))
        || ![reply.baseline_digest, reply.docs_digest, reply.preview_digest].every(value => value === '' || (typeof value === 'string' && DIGEST.test(value)))) {
      throw new Error('Core 返回的绑定或门禁信息无效。');
    }
    return reply;
  }

  function cache(agent, root, reply) {
    if (typeof reply.instructions !== 'string' || !reply.instructions.trim()) throw new Error('当前任务的流程正文未加载。');
    sessions.set(agent.id, { item: reply.item, mode: reply.mode, root, instructions: reply.instructions });
  }

  function describe(reply) {
    const stage = Object.hasOwn(LABELS, reply.stage) ? LABELS[reply.stage] : '待核对阶段';
    const command = reply.mode === 'seeai' ? '/super-dev-seeai' : '/super-dev';
    const headline = `当前任务 ${reply.item}：${stage}`;
    if (reply.stage === 'baseline' && reply.baseline_digest) {
      return `${headline}。核对当前基线后确认此版本：${command} 确认基线 ${reply.baseline_digest}`;
    }
    if (reply.stage === 'docs_confirm' && reply.docs_digest) {
      return `${headline}。先核对三份核心文档；确认此版本：${command} 确认文档 ${reply.docs_digest}`;
    }
    if (reply.stage === 'preview_confirm' && reply.preview_digest) {
      return `${headline}。先核对已验证的预览；确认此版本：${command} 确认预览 ${reply.preview_digest}`;
    }
    if (reply.policy === 'wait' && reply.stage !== 'spec') return `${headline}。当前没有可放行的执行范围。`;
    return `${headline}。如需推进，请使用 ${command} 继续当前流程。`;
  }

  ctx.systemPrompt.section({ name: 'super-dev:dsh-primary', order: 120, interpolate: false,
    text: context => sessions.get(context.agent?.id)?.instructions ?? '' });
  ctx.on('agent/disposed', ({ agent }) => { sessions.delete(agent.id); });
  ctx.on('agent/created', async ({ agent, source }) => {
    if (source !== 'resume') return;
    const binding = scope(agent);
    if (!binding?.mode || binding.child) return;
    try {
      const root = await workspace(ctx, agent);
      if (root) cache(agent, root, await core('instructions', root, agent, binding.mode, binding.item ?? ''));
    } catch { /* The persisted command identity keeps this session fail-closed. */ }
  });

  async function gated(agent, binding, signal) {
    if (binding.child || !binding.item || !binding.instructions) return null;
    try {
      const root = await workspace(ctx, agent);
      if (!root || root !== binding.root) return null;
      return await core('inspect', root, agent, binding.mode, binding.item, '', signal);
    } catch { return null; }
  }

  ctx.on('agent/pre-step', async ({ agent, signal }, next) => {
    const binding = scope(agent);
    if (!binding) return next();
    const reply = await gated(agent, binding, signal);
    return reply && reply.policy !== 'wait' ? next() : { kind: 'reject' };
  });

  ctx.on('tools/pre-execute', async (exec, next) => {
    const binding = exec.agent && scope(exec.agent);
    if (!binding) return next();
    const reply = await gated(exec.agent, binding, exec.signal);
    if (!reply) return deny();
    const cwd = ctx.workingDirectory.get(exec.agent.session);
    if (['read', 'read_image'].includes(exec.name)) return await fileWithin(binding.root, cwd, exec.arguments?.file_path) ? next() : deny();
    if (reply.policy === 'wait') return deny();
    if (exec.name === 'skill') {
      const name = exec.arguments?.name;
      return typeof name === 'string' && !Object.hasOwn(MODES, name.toLowerCase()) ? next() : deny();
    }
    if (['write', 'edit'].includes(exec.name)) {
      const target = await fileWithin(binding.root, cwd, exec.arguments?.file_path, { writing: true });
      if (!target) return deny();
      if (reply.policy === 'draft') return reply.artifacts.includes(target) ? next() : deny();
      const targetKey = target.toLowerCase();
      if (targetKey.split('/').some(part => PROTECTED_NAMES.has(part))) return deny();
      if (reply.policy === 'frontend') {
        const inFrontend = targetKey.startsWith('frontend/') || targetKey.startsWith('output/frontend/');
        const sourceFile = /\.(?:html|css|scss|js|mjs|jsx|ts|tsx|vue|svelte|json|svg|md)$/.test(targetKey);
        return inFrontend && sourceFile && !targetKey.split('/').some(part => part.startsWith('.')) ? next() : deny();
      }
      if (targetKey.startsWith('output/') && !targetKey.startsWith('output/frontend/')) return deny();
      return next();
    }
    // No unscoped Shell, PTC, new child or unverified executor in a managed session.
    return deny();
  });

  for (const [name, mode] of Object.entries(MODES)) {
    ctx.commands.register({ name, description: '在当前 DSH 会话运行 Super Dev 的开发流程',
      input: { hint: '<需求> | 继续当前流程 | 确认基线 <摘要> | 确认文档 <摘要> | 确认预览 <摘要>' },
      async handler(invocation) {
        const { agent, rawInput, signal } = invocation;
        const raw = rawInput.trim();
        if (activating.has(agent.id)) return error('当前会话正在处理另一条 Super Dev 命令。');
        activating.add(agent.id);
        let startDispatched = false;
        try {
          const root = await workspace(ctx, agent);
          if (!root || delegated(agent) || raw.length > 32768) return error('需要已绑定的本地首要会话及有效输入。');
          const action = commandKind(raw);
          const existing = scope(agent);
          if (existing?.mode && existing.mode !== mode) return error('不能在同一任务中切换模式。');
          let reply;
          if (action === 'start') {
            startDispatched = true;
            reply = await core('start', root, agent, mode, existing?.item ?? '', '', signal);
            cache(agent, root, reply);
          } else {
            reply = await core('inspect', root, agent, mode, existing?.item ?? '', '', signal);
          }
          if (action === 'status') return success(describe(reply));
          if (action === 'confirm') {
            const parsed = /^(确认基线|确认文档|确认预览)\s+(\S+)$/.exec(raw);
            if (!parsed || !DIGEST.test(parsed[2])) return error('请在原生命令中提供刚核对过的完整摘要。');
            const operation = { 确认基线: 'confirm-baseline', 确认文档: 'confirm-docs', 确认预览: 'confirm-preview' }[parsed[1]];
            reply = await core(operation, root, agent, mode, reply.item, parsed[2], signal);
            return success(`已记录当前版本的确认。${describe(reply)}`);
          }
          if (action === 'continue') {
            reply = await core(reply.stage === 'spec' ? 'spec' : 'instructions', root, agent, mode, reply.item, '', signal);
            cache(agent, root, reply);
          }
          if (reply.policy === 'wait') return success(`${OWNER}${reply.item}。${describe(reply)}`);
          if (signal?.aborted) return error(action === 'start' ? START_UNCERTAIN : '本次命令已取消，未投递。');
          agent.followup(message(action === 'continue' ? '继续当前已绑定的 Super Dev 工作项，遵循当前 Core 门禁。' : raw));
          return success(`${OWNER}${reply.item}。需求已交给当前 DSH 智能体；实际启动以会话回合为准。`);
        } catch (cause) {
          if (startDispatched && !cause?.bindingUnowned) return error(START_UNCERTAIN);
          return error('无法完整核对当前项目、会话或门禁；未私自继续。');
        } finally { activating.delete(agent.id); }
      },
    });
  }
}
