# 可移植输出与核验

复制整个 skill 文件夹即可迁移指令、模板及渲染器；既有研究历史另行复制工作区 research/，不与安装目录混放。不得依赖用户目录、固定运行日期、Codex 缓存路径或某个浏览器工具名。

## HTML

需要 Node.js 20 或更新版本。Markdown 解析器及许可证已包含在 scripts/vendor/，不需要 npm install、联网或外部字体。先运行 `node --version`；无 Node 时交付 Markdown 并说明 HTML 渲染条件，不冒充完成页面核验。

从任意工作目录运行，脚本路径以实际 skill 安装位置为准：

```sh
node /path/to/ai-ecosystem-research/scripts/render-report.cjs --input /path/to/report.md --output /path/to/report-dark.html --theme dark
```

参数：--input、--output 必填；--theme dark|light 默认 dark；--lang 设置 HTML 语言标记（默认 zh-CN）；--title 可覆盖从首个 H1 提取的标题。脚本不改变原始 Markdown 或研究日期。生成 HTML 内嵌样式与切换按钮，可离线打开；正文中的外部来源链接仍需联网。Markdown 中相对资源链接按源文件目录解析，交付跨电脑版本时将这些资源一起复制并保持相对目录，或改为公开来源 URL。不要将含未信任脚本的原始网页直接作为报告输入；渲染器仅允许无属性的 br 换行标签，转义其余原始 HTML，阻止危险 URL。

## 按交付格式核验

- HTML：检查内容保留、标题层级、事实与分析、宽表滚动、深浅色切换。可访问用户实际页面时必须刷新该页面核验；无桌面能力时用可用渲染环境检查并明确核验范围，不能声称检查了用户屏幕。
- Markdown／聊天：核验标题、表格、来源和正文完整性，不要求网页或主题切换，也不声称控制聊天字号。
- PDF／文档：使用可用的文档导出工具并检查实际页面、跨页表格和链接；缺少工具时保留已完成的源稿，明确不可交付的格式。

格式检查不证明研究事实准确。验收分别记录研究内容、指标口径、模式适配与呈现结果。

HTML 核验先确认实际面板地址与交付文件一致，避免检查旧报告或另一份排版文件。观察摘要、长单元格比较表和末章；检查目录跳转、引用、本地链接及锚点。在可用的窄面板与完整阅读宽度检查：宽表可横向滚动，不靠缩小正文或删去解释解决溢出。切换主题后恢复读者默认主题，保存代表性截图和所检查文件的路径／修订信息。状态过期或多个窗口存在时重新定位目标，不盲目重复点击；无法操作实际页面时限定核验范围。核验不依赖固定窗口 ID、坐标、文件名或某一工具。

## 固定阅读入口

每期完成报告、验收记录及 HTML 后运行：

```sh
python /path/to/ai-ecosystem-research/scripts/build-portal.py --research-dir /path/to/research
```

生成固定 `research/index.html`，包含最新周报、最新月报、历史报告和单独折叠的未验收版本。按研究窗口截止时间、修订/创建时间排序，不以文件修改时间把旧稿误当新稿。新报告仅在 acceptance.json 的 artifact_status=ready 且 delivery_ready=true 时进入最新入口；这只使用已有验收，不替代研究检查。

扫描 runs/ 下的 report-dark.html，读取相邻 run.json。旧报告缺机器验收时，在私有 research/portal-legacy.json 按相对 HTML 路径登记 mode、date、window_start、window_end、title、delivered、label；先核查实际历史交付与限制，再登记。不能修改旧验收或自动将所有 HTML 认作合格。未通过的新验收优先于旧登记。

通知中同时给出固定首页和本期报告的可点击绝对本地文件链接，不仅写“报告已完成”。本地链接不会自动成为 ChatGPT 网页云端页面；不得暗示跨设备可访问。首页采用相对链接，迁移需复制整个 research/。生成的首页、目录索引与旧报告登记均留在私有 research/，不随公开源码上传。无新报告时保留上次阅读入口，不伪造更新日期。
