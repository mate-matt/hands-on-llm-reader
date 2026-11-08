# Hands-On LLM 笔记阅读

个人静态阅读站，用来在浏览器里读 [Hands-On Large Language Models](https://github.com/HandsOnLLM/Hands-On-Large-Language-Models) 的开源笔记本（Jay Alammar 与 Maarten Grootendorst，Apache-2.0）。

这不是 O’Reilly 全书，也不包含书的正文或 PDF。请购买正版：

- [O'Reilly](https://www.oreilly.com/library/view/hands-on-large-language/9781098150952/)
- [Amazon](https://www.amazon.com/Hands-Large-Language-Models-Understanding/dp/1098150961)

线上地址（Pages 打开后）：<https://mate-matt.github.io/hands-on-llm-reader/>

## 这里有什么

- 第 1–12 章 Jupyter 笔记本，转成静态 HTML，保留 Markdown、代码和笔记本里已经保存的输出（包括图片）。
- 上游 `bonus/*.md` 简介，以及这些文件引用的配图。外部长文只给链接，不转载。
- 每章可以在 Colab 打开，并链回上游 `.ipynb`。
- 阅读进度（已读、滚动百分比）只存在本机 `localStorage`。
- 手机宽度（大约 360–430px）是一等布局：底部导航、安全区留白、图片不超过屏幕、代码横向滚动。

## 这里没有什么

- O’Reilly 书的章节散文、书内专有插图和 PDF。
- 付费或订阅站点上的完整图文（Substack、jalammar 文章等）。bonus 页只渲染仓库里的短简介。

上游提交：[`ea339081`](https://github.com/HandsOnLLM/Hands-On-Large-Language-Models/commit/ea3390819997999a51983677b80b3aac4dc50ada)。版权声明见 [NOTICE](NOTICE)，许可证见 [LICENSE](LICENSE)。

## 本地重新生成

```bash
pip install -r requirements-build.txt
python scripts/build_site.py
```

生成结果在 `docs/`。改样式请编辑 `web/css/reader.css` 和 `web/js/reader.js`，再运行上面的脚本。GitHub Actions 会在推送后重跑构建，并检查 `docs/` 是否与源文件一致。

## 打开 GitHub Pages

仓库需要从 `main` 分支的 `/docs` 目录发布：

1. 打开仓库 Settings → Pages。
2. Build and deployment 选 **Deploy from a branch**。
3. Branch 选 `main`，文件夹选 `/docs`，保存。
4. 等一分钟，打开 <https://mate-matt.github.io/hands-on-llm-reader/>。

如果本机的 `gh` 有权限，也可以：

```bash
gh api --method POST repos/mate-matt/hands-on-llm-reader/pages \
  --input - <<'EOF'
{"build_type":"legacy","source":{"branch":"main","path":"/docs"}}
EOF
```

已经开过 Pages 时，把 `POST` 换成 `PUT`。
