# Checklist

## Before High-Risk Tests

- [x] 唯一临时用户目录条件已生效
- [x] `Path.home()`、`expanduser()` 和两个管理器解析一致
- [x] 完整用户级接入面进入真实目录摘要
- [x] 主目录外 `CODEX_HOME` 进入摘要
- [x] Windows 路径同一性和危险目录检查通过
- [x] 隔离自检确认真实用户位置零变化

## Before Delivery

- [x] 两个高风险测试文件在隔离环境完成
- [x] 历史 10、55、35 与当前基线分别登记
- [x] 完整单元检查连续两次结果可比较
- [x] Windows Python 3.10、3.11、3.12 证据已上传
- [x] Ruff、字节码编译、相关类型检查和差异检查通过
- [x] Grok Build 独立审查没有强制问题
- [x] 未修改真实用户级 Skill 或宿主文件
- [x] 未实现扩展平台或九阶段真实控制
- [x] 仅在交付授权后推送功能分支；未合并、未同步用户级 Skill
