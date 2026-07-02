# Git 工作流规范

## 1. 分支命名规范

```
feat/         # 新功能开发
fix/          # Bug 修复
refactor/     # 代码重构（不改变功能）
docs/         # 仅修改文档
chore/        # 依赖/配置/工具变更
hotfix/       # 紧急修复（仅用于生产）
```

示例：`feat/knowledge-graph`、`fix/login-validation`

## 2. 提交信息格式（Conventional Commits）

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型
| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构 |
| docs | 文档 |
| chore | 构建/工具/依赖 |
| test | 测试 |
| style | 代码格式（不影响逻辑） |
| perf | 性能优化 |

### 示例
```
feat(admin): 新增知识图谱语义边生成逻辑
fix(route): 修复文件上传接口路径错误
refactor(admin_routes): 重构知识图谱逻辑，新增语义边支持
```

## 3. 分支策略（GitHub Flow 简化版）

```
master (保护分支)
  └── feat/xxx     ← 功能分支，开发完成后合并
  └── fix/xxx      ← 修复分支，完成后合并
```

### 合并流程
1. 从 `master` 拉取新分支
2. 开发完成后提交到远程
3. 创建 Pull Request / Merge Request
4. 至少 1 人 Review 后合并
5. 合并后立即删除功能分支

### 紧急修复流程
```
master ──→ hotfix/urgent-fix ──→ master
                          └────→ feature/xxx（cherry-pick）
```

## 4. 代码审查 Checklist

- [ ] 代码逻辑正确，无明显的语法错误
- [ ] 遵循项目编码规范
- [ ] 新功能有对应的测试（如适用）
- [ ] 提交信息遵循 Conventional Commits 格式
- [ ] 无敏感信息泄露（密钥、token、.env 等）
- [ ] 无不必要的文件变更（如 node_modules、__pycache__）

## 5. 禁止提交的文件

```
node_modules/     # 通过 npm install 恢复
__pycache__/      # Python 字节码缓存
.DS_Store         # macOS 系统文件
*.db              # 数据库文件
*.sqlite3         # SQLite 数据库
chroma_db/        # 向量数据库
.env              # 环境配置（使用 .env.example）
```

## 6. 常用命令

```bash
# 查看当前状态
git status --short

# 仅查看特定目录状态
git status --short admin/ backend/

# 清理 stash
git stash drop stash@{0}

# 清理孤立对象（仓库瘦身）
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# 查看仓库大小
du -sh .git/
```
