# 贡献指南

感谢你对 Campus Guide Agent 的关注！

## 贡献方式

### 🏫 添加你的大学

这是最简单也最有价值的贡献方式！只需要：

1. Fork 本项目
2. 在 `config/universities/` 下创建 `your_uni.yaml`
3. 在 `data/your_uni/` 下用 Markdown 编写校园知识
4. 运行 `python scripts/init_db.py --university your_uni` 验证
5. 提交 PR

#### Markdown 编写规范

知识文件放在 `data/<大学ID>/` 目录下：

```
data/your_uni/
├── teachers/          # 教师信息（每个学院一个 .md 文件）
│   ├── 计算机学院.md
│   └── 文学院.md
├── food/              # 美食信息
│   └── 美食指南.md
└── campus/            # 校园设施
    ├── 新生FAQ.md
    └── 校园地图.md
```

Markdown 格式要求：

```markdown
# 学院/食堂名称（一级标题 = 大类标签）

## 具体人/窗口（二级标题 = sub-chunk 边界）
- 用无序列表写属性
- 每个要点一行
```

### 🔌 编写数据源插件

如果你的大学有网页/小程序/API 可以获取校园数据，请编写插件：

1. 在 `plugins/your_uni/` 下创建 Python 文件
2. 继承 `core.ingest.base.DataSourcePlugin`
3. 实现 `load()` 和 `validate()` 方法
4. 在 `config/universities/your_uni.yaml` 中注册

### 💻 代码贡献

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 运行测试 (`pytest tests/`)
4. 提交 PR

## PR 规范

- PR 标题简洁明确（中英文均可）
- 描述你的改动内容和原因
- 如果是新功能，附带使用示例
- 通过所有 CI 检查
