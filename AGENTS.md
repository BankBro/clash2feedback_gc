# clash2feedback_gc 协作规范

## 1. 全局规则

- 交互语言: 与仓库内 Agent 及用户交互时一律使用中文.
- 输出编码: 所有写入文件或终端的文本一律使用 UTF-8.
- 标点规范: 中文文本统一使用英文标点.
- 实现原则: 保持实现简洁, 优先服务项目目标, 避免过度工程化.
- 代码边界: 代码标识符, 日志, 错误信息, 配置键名等优先使用英文; 注释和文档可使用中文.
- 复用优先: 优先使用已有模块, 工具链和标准库能力.
- 预读要求: 修改某个目录前, 先阅读根目录和该目录下最近的 `AGENTS.md`.
- 文档同步: 每次项目结构, 行为或使用方式变化时, 同步更新相应目录下的 `README.md`, 删除过时内容, 并保持文档简洁凝练.
- HF 下载: 使用 Hugging Face 数据或模型文件前, 优先检查可用镜像; 镜像可用时优先通过镜像下载, 并在记录中保留原始来源. 下载缓存应显式放入本项目相关目录, 优先使用 `data/cache/`, 避免写入默认 `~/.cache/huggingface`.
- 外部 baseline: `external/` 下的外部源码和 checkpoint 默认不提交 Git. 需要长期复现或让外部读者访问源码时, 先查 `docs/external_baselines.md` 中记录的 source repo, pinned commit, checkpoint URL 和关键代码路径, 不要假设远端读者能看到本地 `external/` 目录.

## 2. 目录索引

根目录只保留目录索引, 具体约束下沉到各主目录的 `AGENTS.md`.

| 目录 | 职责 |
|---|---|
| `docs/` | 人工维护的方案文档 |
| `configs/` | 每阶段配置文件 |
| `data/` | 原始数据, 处理数据, 划分, benchmark, candidate pool 和缓存 |
| `external/` | 外部 baseline 仓库和公开 checkpoint 的本地副本 |
| `reports/` | 各阶段统计表, 图, summary 和检查报告 |
| `runs/` | 日志, checkpoint, 生成候选等较重运行产物 |
| `src/` | `clash2feedback` Python 包源码 |
| `scripts/` | 各阶段命令行入口 |
| `tmp/` | 按日期归档的临时文件, 中间脚本和一次性输出 |

统一约定:

- Python 包名为 `clash2feedback`, 路径为 `src/clash2feedback/`.
- 阶段入口统一命名为 `scripts/phaseN_*.py`.
- 不使用顶层 `outputs/`.
- 不在 `src/` 下新增 `experiments/` 作为命令入口.

## 3. 变更管理

- 最小变更: 只改与目标直接相关的文件.
- Git 读操作可直接执行, 例如 `status`, `log`, `diff`, `show`.
- Git 写操作需要用户明确同意, 例如 `commit`, `branch`, `reset`, `merge`, `rebase`, `push`.
- 分支命名: 创建新分支时统一使用 `YYYMMDD-HHMMSS-具体分支名` 格式, 除非用户指定其他格式.
- 临时文件: 临时文件, 中间脚本和一次性输出暂时保存在本项目的 `tmp/` 目录下, 轻量 Markdown 复盘按 `tmp/YYYYMMDD/` 日期子目录归档.
- 不粗暴回退用户已有修改; 遇到相关改动时先理解并兼容.
- 禁止执行高风险破坏性命令; 涉及删除, 覆盖, 权限提升或环境级修改时先确认.

## 4. Markdown 规范

- 文档总标题使用 `# 标题`.
- 一级章节使用 `## N. 标题`, 子节使用 `### N.M. 标题`, 最多到 H3.
- 无序列表使用 `-`.
- 命令, 配置和代码使用围栏代码块.
- 代码块内不使用 emoji.
