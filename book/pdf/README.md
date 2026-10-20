# PDF 排版

这里维护当前 Quarto PDF 的封面图片、LaTeX 样式与标题页片段。样式参考历史 ElegantBook 版的全幅校园封面、深蓝色封面横带、蓝色章节标题与页眉页脚；正文继续由当前 `.qmd` 生成。

`cover.jpg` 是历史版 `cover3.jpg` 的发布副本。构建不读取 `archive/`，使用 XeLaTeX、`ctexbook` 和发行版自带的 Fandol 中文字体。修改后应完整构建，并查看封面、目录、正文、表格和插图页。
