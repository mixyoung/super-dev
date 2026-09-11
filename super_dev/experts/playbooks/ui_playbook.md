# UI设计师（UI）操作手册

> 使用范围：这是 UI 的按需方法参考，职责与交接见[专家设定](../builtin/UI.md)。按当前请求选择相关章节，复用已有决定；示例数值、模板和流程不自动成为新需求或覆盖项目已确认门禁。只读审查给出发现，实施和外部操作依据已有授权。

## 概述

UI设计师负责构建一致、专业、可扩展的视觉系统。核心职责包括设计Token系统定义、组件视觉规范制定、品牌一致性守护、跨端适配策略、视觉质量审查。UI设计不是装饰，而是通过视觉语言传递信息层级、引导用户行为、建立品牌信任。

### 核心原则

1. **系统化而非碎片化**：所有视觉决策基于Token系统，而非逐页手动调整
2. **一致性优于创意**：同一产品内视觉语言必须统一，减少用户认知负担
3. **克制而非堆砌**：少用装饰元素，让内容本身成为视觉焦点
4. **可访问性内建**：色彩对比度、字号、触控区域在设计阶段就满足无障碍标准

---

## 方法论

### 一、设计Token系统

#### 1.1 颜色Token

```
语义化颜色（不用原始色值命名）:

品牌色:
  --color-brand-primary: #1a73e8      主行动色
  --color-brand-primary-hover: #1557b0 悬停态
  --color-brand-primary-pressed: #0d47a1 按下态
  --color-brand-secondary: #34a853    辅助色

语义色:
  --color-semantic-success: #0d8043
  --color-semantic-warning: #e8a000
  --color-semantic-error: #d93025
  --color-semantic-info: #1a73e8

中性色（灰阶）:
  --color-neutral-900: #1a1a1a    主文本
  --color-neutral-700: #4a4a4a    次要文本
  --color-neutral-500: #8a8a8a    辅助文本/占位符
  --color-neutral-300: #d0d0d0    边框/分割线
  --color-neutral-100: #f5f5f5    背景色
  --color-neutral-50:  #fafafa    次级背景

背景色:
  --color-bg-primary: #ffffff
  --color-bg-secondary: #f8f9fa
  --color-bg-tertiary: #f1f3f4
  --color-bg-inverse: #1a1a1a

暗色模式映射:
  每个语义Token需定义对应的dark mode值
  使用CSS custom properties或主题上下文切换
```

#### 1.2 字体Token

```
字体家族:
  --font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont,
                      'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif
  --font-family-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace

字号阶梯（基于 1.25 比率）:
  --font-size-xs:   0.75rem   (12px)  标注/角标
  --font-size-sm:   0.875rem  (14px)  辅助文本
  --font-size-base: 1rem      (16px)  正文
  --font-size-lg:   1.25rem   (20px)  小标题
  --font-size-xl:   1.5rem    (24px)  节标题
  --font-size-2xl:  2rem      (32px)  页标题
  --font-size-3xl:  2.5rem    (40px)  大标题/Hero

字重:
  --font-weight-regular: 400   正文
  --font-weight-medium:  500   强调
  --font-weight-semibold: 600  标题
  --font-weight-bold:    700   大标题

行高:
  --line-height-tight:  1.25   标题
  --line-height-normal: 1.5    正文
  --line-height-relaxed: 1.75  长文本
```

#### 1.3 间距Token

```
基础间距（4px 网格）:
  --spacing-0:   0
  --spacing-1:   0.25rem  (4px)
  --spacing-2:   0.5rem   (8px)
  --spacing-3:   0.75rem  (12px)
  --spacing-4:   1rem     (16px)
  --spacing-5:   1.25rem  (20px)
  --spacing-6:   1.5rem   (24px)
  --spacing-8:   2rem     (32px)
  --spacing-10:  2.5rem   (40px)
  --spacing-12:  3rem     (48px)
  --spacing-16:  4rem     (64px)

语义间距:
  --spacing-page-margin:    1.5rem (移动端) / 4rem (桌面端)
  --spacing-section-gap:    4rem (移动端) / 6rem (桌面端)
  --spacing-card-padding:   1rem (移动端) / 1.5rem (桌面端)
  --spacing-form-gap:       1rem
  --spacing-inline-gap:     0.5rem
```

#### 1.4 阴影Token

```
--shadow-sm:   0 1px 2px rgba(0,0,0,0.05)       微弱阴影（卡片）
--shadow-md:   0 4px 6px -1px rgba(0,0,0,0.1)    中等阴影（浮层）
--shadow-lg:   0 10px 15px -3px rgba(0,0,0,0.1)  强阴影（弹窗）
--shadow-xl:   0 20px 25px -5px rgba(0,0,0,0.1)  最强阴影（模态框）

使用规则:
  阴影层级反映Z轴高度关系
  同一界面最多使用3种阴影等级
  暗色模式下阴影需调整为更深的背景色差异
```

#### 1.5 圆角Token

```
--radius-none: 0
--radius-sm:   0.25rem  (4px)   按钮/输入框
--radius-md:   0.5rem   (8px)   卡片
--radius-lg:   0.75rem  (12px)  大卡片/弹窗
--radius-xl:   1rem     (16px)  特殊容器
--radius-full: 9999px            圆形/药丸按钮
```

---

### 二、组件设计规范

#### 2.1 全状态矩阵

对组件实际存在的交互定义相应状态；下表为候选，不为静态组件新增无关行为：

| 状态 | 描述 | 视觉变化 |
|------|------|---------|
| Default | 默认静止状态 | 基准样式 |
| Hover | 鼠标悬停 | 背景变浅/加深、微弱阴影 |
| Focus | 键盘聚焦 | 2px outline（品牌色）、不得与hover相同 |
| Active/Pressed | 按下 | 背景加深、微缩放（scale 0.98） |
| Disabled | 不可交互 | 降低透明度(0.5)、cursor: not-allowed |
| Loading | 加载中 | 旋转指示器、禁止重复点击 |
| Error | 错误状态 | 红色边框、错误提示文本 |
| Success | 成功状态 | 绿色边框/对勾图标 |

#### 2.2 按钮规范

```
层级体系:
  Primary:   填充品牌色背景，白色文字（每页最多1-2个）
  Secondary: 品牌色边框，透明背景
  Tertiary:  无边框，纯文本，品牌色
  Danger:    填充红色背景（仅用于删除/不可逆操作）

尺寸:
  Small:  高度 32px，padding 8px 12px，font-size 14px
  Medium: 高度 40px，padding 10px 16px，font-size 14px
  Large:  高度 48px，padding 12px 24px，font-size 16px

间距规则:
  按钮组间距: 8px
  按钮内图标与文字间距: 8px
  最小宽度: 80px（防止按钮过窄）
```

#### 2.3 表单输入规范

```
尺寸:
  高度: 40px（与Medium按钮对齐）
  内边距: 10px 12px
  标签与输入间距: 6px
  输入项间距: 16px

视觉:
  边框: 1px solid --color-neutral-300
  圆角: --radius-sm
  聚焦: 边框变为品牌色 + 外发光
  错误: 边框变为错误色 + 下方显示错误文本

必填标记: 标签后红色星号(*)
帮助文本: 输入框下方，使用 --color-neutral-500，font-size-sm
字符计数: 右下角显示，接近上限时变为警告色
```

---

### 三、品牌一致性检查

```
检查维度:
  1. 所有页面是否使用统一的Token系统
  2. 品牌色使用是否准确（禁止近似色替代）
  3. 字体家族是否统一（禁止混用多套字体）
  4. 图标风格是否一致（线性/填充/双色统一风格）
  5. 插图/配图风格是否协调
  6. 间距是否遵循4px网格
  7. 语气和措辞是否与品牌调性一致
```

---

### 四、跨端适配策略

```
断点定义:
  --breakpoint-sm:  640px   (手机竖屏)
  --breakpoint-md:  768px   (平板竖屏)
  --breakpoint-lg:  1024px  (平板横屏/小笔记本)
  --breakpoint-xl:  1280px  (桌面)
  --breakpoint-2xl: 1536px  (大屏)

适配原则:
  移动优先: 先设计移动端布局，再向上适配
  内容优先: 小屏隐藏装饰元素，保留核心内容
  触控适配: 移动端可点击区域最小 44x44px
  排版适配: 移动端减少列数，增大字号间距

布局策略:
  桌面端: 12列网格，最大宽度1280px居中
  平板端: 8列网格
  手机端: 4列网格，全宽
  侧边栏: 桌面端展开，平板端可收起，手机端底部Tab或抽屉
```

---

### 五、避免AI模板化视觉

```
必须避免的AI模板特征:
  1. 紫色/蓝紫渐变背景作为主视觉
  2. 大面积毛玻璃效果无实际用途
  3. 用emoji代替专业图标
  4. 无层次感的平铺卡片布局（所有卡片视觉权重相同）
  5. 缺乏留白，信息密度过高或过低
  6. 默认系统字体无排版处理
  7. 通用库存图片充当Hero图
  8. 装饰性动画过多且无用途
  9. 全彩图标与界面色调不协调
  10. 无品牌识别度（换个Logo就能用于任何产品）

应该做的:
  - 建立真实的品牌色板，而非随意渐变
  - 使用高质量插图/截图替代库存图
  - 信息层次通过字重/字号/颜色区分，而非装饰
  - 适度留白，让内容呼吸
  - 交互反馈精确而克制（不滥用过渡动画）
```

---

## UI审查检查清单

### Token系统审查

- [ ] 是否定义了完整的颜色Token（品牌色/语义色/中性色/背景色）
- [ ] 是否定义了字体阶梯（不超过7级）
- [ ] 是否定义了间距系统（基于4px网格）
- [ ] 是否定义了阴影和圆角等级
- [ ] 暗色模式是否有对应的Token映射
- [ ] 所有组件是否引用Token而非硬编码色值

### 组件规范审查

- [ ] 所有交互组件是否定义了完整状态（default/hover/focus/active/disabled/loading/error）
- [ ] 按钮是否有清晰的层级体系（primary/secondary/tertiary）
- [ ] 表单输入是否规范（标签/占位符/帮助文本/错误提示/必填标记）
- [ ] 组件尺寸是否对齐（按钮高度与输入框高度一致）
- [ ] 是否定义了组件间距规范
- [ ] 图标是否风格统一（尺寸/粗细/风格）

### 品牌一致性审查

- [ ] 品牌色使用是否准确（禁止近似色）
- [ ] 字体家族是否统一
- [ ] 图标风格是否一致
- [ ] 页面间视觉语言是否连贯
- [ ] 产品截图/插图风格是否协调

### 跨端适配审查

- [ ] 断点是否合理定义
- [ ] 移动端触控区域是否>=44px
- [ ] 小屏是否隐藏了装饰元素保留核心内容
- [ ] 文字在各断点下是否可读（最小14px）
- [ ] 布局是否在各断点下正常显示

### 反模板化审查

- [ ] 是否避免了紫色/蓝紫渐变作为主视觉
- [ ] 是否避免使用emoji代替专业图标
- [ ] 是否有真实的品牌识别度（而非通用模板）
- [ ] 装饰元素是否克制且有明确用途
- [ ] 信息层次是否通过排版而非装饰来传达

---

## 交叉审查要点

### 与UX设计师交叉

- 视觉层次是否服务于信息架构
- 状态设计（空/加载/错误）是否有对应的视觉方案
- 动效是否传达了有意义的状态变化

### 与前端开发交叉

- Token系统是否可直接转化为CSS变量/主题配置
- 组件状态是否覆盖了所有代码中的条件分支
- 响应式断点是否与前端框架一致

### 与产品交叉

- 视觉焦点是否引导用户完成核心任务
- CTA按钮是否足够突出
- 信任模块（证书/案例/数据）是否在合适位置

---

## 常见反模式

| 反模式 | 问题 | 正确做法 |
|-------|------|---------|
| 色值散落 | 50种灰色散落在代码中 | 统一使用Token系统 |
| 字号随意 | 13px/15px/17px无规律 | 使用字号阶梯 |
| 状态缺失 | 按钮只有默认态 | 8态全覆盖 |
| 装饰过度 | 渐变+阴影+动画+圆角堆砌 | 克制，服务于信息传达 |
| 间距随机 | 组件间距10/13/17px无规律 | 遵循4px网格系统 |
| 图标混搭 | 线性+填充+彩色图标混用 | 统一图标风格 |
| 无障碍缺失 | 对比度不足/焦点不可见 | WCAG AA标准内建 |

---

## 知识依据

- **Token系统**：Design Tokens W3C Community Group 规范、Salesforce Lightning Design System
- **组件规范**：Material Design 3、Ant Design、Radix UI
- **色彩理论**：WCAG 2.1 色彩对比度标准（AA级4.5:1，AAA级7:1）
- **排版**：Practical Typography（Butterick）、Inter字体设计文档
- **响应式**：Ethan Marcotte《Responsive Web Design》、Container Queries规范
- **反模板化**：Super Dev UI Intelligence反模式库
