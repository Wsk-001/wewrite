# 学习人工修改（核心飞轮）

## 1. 获取 draft 和 final

- draft：output/ 下最新的 .md 文件
- final：用户提供修改后的版本

## 2. 运行 diff 分析

```bash
python3 {skill_dir}/scripts/learn_edits.py --draft {draft_path} --final {final_path}
```

## 3. 分析并记录 pattern

每个 pattern 包含：type、key、description、rule

## 4. Playbook 更新

每积累 5 次 lessons，触发 playbook 更新。

## 5. Step 4 如何使用 playbook

- confidence ≥ 5：硬性约束
- confidence 3-5：软性参考
- confidence < 3：忽略
