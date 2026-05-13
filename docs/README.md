# docs

## 1. 目录定位

`docs/` 只放人工维护的方向性文档, 例如总体方案, 阶段方案, 设计说明, 路线规划和 baseline 说明.

## 2. 放置规则

- 实验结果, 阶段最终报告, 审计报告, summary, `csv`, `parquet`, `jsonl`, `trace` 等结果文件应放入 `reports/`.
- 训练日志, checkpoint, 生成候选和渲染图等运行产物应放入 `runs/`.
- 临时复盘, 交接 prompt 和网页 ChatGPT 分析上下文应放入 `tmp/`.

## 3. 事实优先级

仓库真实结果文件优先于 `docs/` 中的方案描述. 写作时不得把未验证设想写成已完成结论, 不得臆造实验数据.

## 4. 阶段 3 / 4 当前口径

- 阶段 3 仍叫阶段 3, 定位为 label provenance audit, circularity risk audit, construction consistency check 和 phase4 mask seed generation.
- `supported_single_rgroup` 上的 Top-1 / Top-3 只能作为 construction consistency check, 不作为 independent locator benchmark.
- 阶段 4 的 predicted mask 是 operational mask policy, 不是 ground truth; 阶段 4 先做 backend feasibility audit, 再做 Random / Predicted / Oracle formal repair loop.
- `reports/phase2_injection/phase2_final_report.md` 是历史阶段 2 关闭报告, 其中保留的阶段 3 Top-1 / Top-3 建议属于旧口径; 当前后续执行以本目录更新后的阶段 3 新口径为准, 不回写历史实验报告.
