# Mobile Formatter · 本地通用手机适配排版工具

参考 [xhs-formatter](https://github.com/antonia-sz/xhs-formatter) 的移动端卡片排版思路，结合原生浏览器高保真渲染，支持 **Markdown / HTML / 纯文本** 转为适合手机阅读的网页或高清长图。

## 在线使用

访问 https://youfun.github.io/mobile-formatter/ 即可使用网页工作台，无需安装。

网页为纯静态页面，输入内容在浏览器中处理，并保存在当前浏览器的本地存储中。字体使用访问设备的系统字体，不同系统的显示效果可能略有差异；PNG 导出依赖从 jsDelivr 加载的 html2canvas。

GitHub Pages 从 `main` 分支根目录发布，推送更新后自动重新部署。`mobile_format.py` 仅供本地命令行使用，不会在 Pages 上运行。

## 目录结构

- `index.html`：本地可视化排版工作台（浏览器直接打开即可使用，支持拖拽导入、实时预览、参数调节、长图与分页导出）。
- `mobile_format.py`：命令行批量/自动化排版脚本（调用本地 `agent-browser` 无头 Chromium 渲染，完整保留原 HTML 的代码高亮、链接与强调颜色）。

## 方式一：可视化工作台 (`index.html`)

直接双击打开，或启动本地静态服务器：

```bash
cd /Volumes/SSD/dev/learn-e/mobile-formatter
python3 -m http.server 8080
```

浏览器访问 `http://localhost:8080`：
1. 左侧粘贴、输入或拖入 `.md` / `.html` / `.txt` 文件；
2. 中间选择排版主题（极简阅读、小红书风、公众号风、知乎专栏、暗夜护眼），调节手机宽度、字号、行高、段距与首行缩进；
3. 右侧实时查看手机竖屏效果，点击顶部按钮导出 **整张长图 (PNG)**、**3:4 分页图** 或 **自适应手机版 HTML**。

## 方式二：命令行工具 (`mobile_format.py`)

适合处理长文或直接从已有的 HTML（保留原有高亮颜色）生成手机高清长图：

```bash
# 1. 将 Markdown 转为手机适配高清长图
python3 /Volumes/SSD/dev/learn-e/mobile-formatter/mobile_format.py \
  /Volumes/SSD/dev/learn-e/epistemic-learned-helplessness-zh.md \
  -o /Volumes/SSD/dev/learn-e/epistemic-learned-helplessness-zh-mobile.png \
  --theme minimal --font-size 18 --width 430

# 2. 将已有 HTML（保留原有高亮与链接颜色）转为手机版长图
python3 /Volumes/SSD/dev/learn-e/mobile-formatter/mobile_format.py \
  /Users/box/Downloads/epistemic-learned-helplessness-zh.html \
  -o /Users/box/Downloads/epistemic-learned-helplessness-zh-cli.png

# 3. 导出为自适应手机版 HTML
python3 /Volumes/SSD/dev/learn-e/mobile-formatter/mobile_format.py \
  input.md -o output-mobile.html --theme wechat
```
