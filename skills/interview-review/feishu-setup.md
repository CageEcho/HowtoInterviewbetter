# 一键建飞书结构（feishu-setup）

触发：用户说「帮我建面试复盘飞书结构」「初始化面试记录表」「帮我搭面试复盘知识库」。

## 0. 前提
- AI 助手能调用飞书开放平台接口：官方命令行 `lark-cli`，或飞书 MCP / 插件，或直接调 OpenAPI。
- 同学用**自己的账号**在 https://open.feishu.cn/app 创建自建应用，并完成**用户授权**（user_access_token），这样建出的文档归同学本人所有。
- 需要的权限范围（在开放平台「权限管理」里开通）：
  - 知识库：`wiki:wiki`（读写节点）
  - 云文档：`docx:document`（创建/编辑文档）
  - 多维表格：`bitable:app`（创建表格、字段）；`base:record:create` / `base:record:retrieve`（写示例行、删默认空行，缺了会跳过并提示）
  - 可选：`drive:drive`（上传逐字稿 PDF）
- 不要把任何 App ID / Secret / token 写进文档或聊天记录。

## 1. 先问清楚
1. 姓名（必填），学号（可选，填了则命名为「学号-姓名-xxx」）。
2. 目标知识库 `space_id`（在知识库设置里或用 `GET /open-apis/wiki/v2/spaces` 查），以及要挂在哪个父节点下（可选，默认根）。
3. 先 `--dry-run` 把计划给用户确认，再真实创建。

## 2. 要建的节点（前缀 P = 「学号-姓名」或「姓名」）
每个文档的正文都来自 `templates/feishu/*.xml`（飞书 XML，`{P}` 会替换成前缀），建好即带：🟧说明框 + 🟦建设攻略 + （示例）内容。

| # | 标题 | 类型 | 正文来源 |
|---|---|---|---|
| 0 | P-个人面试记录表&复盘 | docx | 00-总入口.xml（目录用 @文档 引用自动生成） |
| 1 | P-个人简历在线综合 | docx | 01-个人简历在线综合.xml |
| 2 | P-个人飞书版简历 | docx | 02-个人飞书版简历.xml |
| 3 | P-简历+打招呼语+面试 详细方法论 | docx | 10-简历打招呼语面试方法论.xml |
| 4 | P-面试表 | bitable | 字段与示例行见 `templates/面试表Bitable字段定义.json` |
| 5 | P-面试复盘存档（一次面试一个文档，按模板） | docx | 03-面试复盘存档.xml |
| 5.1 | 复盘模板 | docx | 03a-复盘模板.xml |
| 5.2 | P-周总文档（每周汇总） | docx | 03b-周总文档.xml |
| 5.3 | （案例）某软件公司（二面）-AI 产品经理 | docx | 03c-案例复盘.xml |
| 6 | P-打分表 | docx | 04-打分表.xml |
| 7 | P-测试题复盘（一次测试题一个文档） | docx | 05-测试题复盘.xml |
| 7.1 | （案例）某大厂AI助手（一面）-竞品分析测试题 | docx | 05a-案例测试题.xml |
| 8 | P-个人战略（1v1复盘+面试策略） | docx | 06-个人战略.xml |
| 9 | P-个人面试话术文档（自我介绍+打招呼语） | docx | 07-个人面试话术文档.xml |
| 10 | P-穷尽面试问题汇总（以问题为单位） | docx | 08-穷尽面试问题汇总.xml |
| 11 | P-面试经验沉淀（以条为单位） | docx | 09-面试经验沉淀.xml |

`--no-examples` 不建 5.3 / 7.1，也不写示例行。简历 PDF 不建节点，提示同学把最新 PDF 作为附件放到总入口第 2 条下。各页面写什么、怎么写见 `book/12-各板块建设攻略与示例.md`。

## 3. 建立步骤
1. **列已有节点**：`GET /open-apis/wiki/v2/spaces/{space_id}/nodes?parent_node_token=...`（分页取全）。同名标题直接复用其 token，**跳过不建、也不覆盖正文**。
2. **建总入口**与所有子节点（`POST /open-apis/wiki/v2/spaces/{space_id}/nodes`），面试表 `obj_type=bitable`。
3. **配面试表**：由 wiki 节点拿到 `obj_token`（即 app_token）→ 列 tables → 首列改名「公司&团队」→ 按 JSON 逐个新增字段 → **删除新表自带的默认列（单选 / 日期 / 附件等）** → 删除默认空行（需 `base:record:retrieve`）→ 写入 `example_records` 的 2 行（示例）记录（需 `base:record:create`）。
4. **写正文**：`lark-cli docs +update --doc <obj_token> --command overwrite --doc-format xml --content @file.xml`。
   - **必须用 XML，不要用 markdown**：markdown 覆盖会把文档标题改成正文第一行，而且高亮块颜色会丢。XML 以 `<title>` 开头，标题不变。
   - 高亮块写法：`<callout emoji="🎹" background-color="light-orange" border-color="orange"><p>…</p></callout>`；callout 里只能放 `p/ol/ul/checkbox`，不能放标题和表格。颜色：橙 light-orange/orange，红 light-red/red，灰 gray/gray，蓝 light-blue/blue，绿 light-green/green，黄 light-yellow/yellow。部分 emoji（🟢🟡🧭）会被飞书换成 💡，颜色不受影响。
   - 红字：`<span text-color="red">…</span>`。
5. **总入口最后写**：所有子节点建好后，用 `<cite type="doc" doc-id="<obj_token>"/>` 生成目录（不依赖域名）。
6. **回读核对**：`lark-cli docs +fetch --doc <token> --detail full` 看高亮块 `background-color` 是否在；列面试表字段与 JSON 比对（应正好 10 个）。
7. **输出清单**：每个节点的标题、类型、链接（`https://<你的域名>.feishu.cn/wiki/<node_token>`）。

## 4. 幂等与防重复
- 每一步建之前都先查同名；脚本可重复执行，第二次运行应全部显示「跳过」。
- 正文只对本次新建的文档写入；已存在的同名文档不覆盖。确需修复自己刚建的空页面时加 `--overwrite`（会整页覆盖，先问用户）。

## 5. 权限（AI 不要自动改）
建完后提醒同学：先检查没有真实薪资、面试官姓名、公司内部信息，再**自己**在分享设置里设为「互联网获得链接的人可编辑」，并勾选对子页面生效。AI 不调用权限接口放开分享。

## 6. 降级方案
- 无飞书接口：按第 2 节表格手工建；面试表按 JSON 手工加字段；复盘模板手工粘贴。
- 有公开模板：打开模板 →「…」→ 创建副本，**勾选「同时创建子页面的副本」**，再把标题前缀改成自己的。
- 不用飞书：任意文档工具 + 表格按同样结构建即可，方法不绑定工具。

参考脚本：`scripts/setup_feishu.py`（默认 `--dry-run`）。
