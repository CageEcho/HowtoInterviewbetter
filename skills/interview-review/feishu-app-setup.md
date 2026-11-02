# 飞书自建应用、space_id 与常见报错（脚本路线 ② 的准备）

> 只想要一套现成结构？先用 README 里的 **路线 ① 零配置：手动复制模板**，不用做本页任何事。

## 一、创建飞书自建应用（纯文字步骤）

1. 用**自己的飞书账号**打开 https://open.feishu.cn/app ，点「创建企业自建应用」，填名称（如「面试复盘助手」）和描述，创建。
2. 进入应用 →「凭证与基础信息」，记下 App ID / App Secret。**只存在本机，不要贴进文档、聊天或仓库。**
3. 「权限管理」→ 搜索并开通下面全部权限（用户身份 user_access_token 那一栏要勾上）：

| 权限 | 脚本里用到的地方 |
| --- | --- |
| `wiki:wiki` | 列出/创建知识库节点（`/wiki/v2/spaces/{space}/nodes`） |
| `docx:document` | 往文档写攻略、示例和三色框（`lark-cli docs +update`） |
| `bitable:app` | 读数据表、增删改字段（`/bitable/v1/apps/.../tables`、`fields`） |
| `base:record:retrieve` | 读记录，找出飞书自带的默认空行 |
| `base:record:create` | 写 2 行示例数据（`records/batch_create`） |
| `base:record:delete` | 删除默认空行（`records/batch_delete`） |
| `drive:drive`（可选） | 上传逐字稿 PDF、设置分享 |

4. 「安全设置」→ 重定向 URL：按 lark-cli 文档要求填写（通常是本机回调地址）。
5. 「版本管理与发布」→ 创建版本 → 提交发布。企业版需要管理员审核；个人版/自己是管理员时直接通过。**权限改动后都要重新发版才生效。**
6. 把应用加进知识库：打开目标知识库 →「设置」→「成员设置」→ 添加成员，搜索应用名，给「可编辑」或「管理员」。用用户身份调用时，你本人也必须是该知识库的可编辑成员。
7. 本机安装并登录 lark-cli（命令以官方文档为准）：先配置 App ID/Secret，再执行用户登录，浏览器里点「授权」。登录后用 `lark-cli api GET /open-apis/wiki/v2/spaces` 能列出你的知识库，就说明通了。

## 二、找 space_id 和父节点 token

- **父节点 token**：打开知识库里想挂在其下的页面，地址 `https://xxx.feishu.cn/wiki/<这一串>` 里 `/wiki/` 后、`?` 前那串就是 node token，用作 `--parent`。
- **space_id**（数字串）任选一种：
  - `lark-cli api GET /open-apis/wiki/v2/spaces/get_node --params '{"token":"<node token>"}'`，返回里的 `space_id`；
  - `lark-cli api GET /open-apis/wiki/v2/spaces`，按名称找；
  - 知识库「设置」页地址里常带 space id。
- 然后：`python3 skills/interview-review/scripts/setup_feishu.py --space-id <space_id> --parent <node token> --name 你的名字`（先看 dry-run，确认后加 `--execute`）。

## 三、常见报错对照

| 现象 / 报错 | 原因 | 解决 |
| --- | --- | --- |
| `99991679` / `missing_scope` / Unauthorized | 应用没开该权限，或开了没发版，或登录时没授权到 | 按上表补权限 → 重新发布版本 → 重新 lark-cli 登录授权 |
| 面试表多出「文本 / 单选 / 日期 / 附件」等默认列、几行空行 | 新建多维表格自带默认字段和空记录 | 脚本会删；缺 `base:record:*` 时删不掉空行，手动删或补权限重跑 |
| 文档标题被改成正文第一行 | 用 markdown 覆盖写入时首个 `# 标题` 会被当成文档标题 | 脚本正文不以一级标题开头；手工写时去掉开头的 `#` 标题，或写完再改回标题 |
| 彩色高亮框变成普通引用/文字 | 普通 markdown 没有 callout 语法 | 用 `templates/feishu/` 里带 `<callout background-color=... border-color=...>` 的版本写入；或在飞书里手动「/高亮块」后选颜色 |
| 高亮框图标都是 💡 | callout 未指定 emoji，飞书用默认图标 | 在 callout 上写 `emoji="white_check_mark"` 等；或在飞书里点图标改 |
| 添加节点 permission denied / `131006` / 无权限 | 你或应用不是该知识库可编辑成员 | 知识库「成员设置」里把自己和应用加为可编辑/管理员 |
| `131005 not found` | space_id 与 node token 不属于同一知识库，或 token 抄错 | 用 get_node 重新查 space_id |
| 别人点链接打不开 | 文档只对本企业可见 | 文档「分享」→「互联网上获得链接的人可阅读」；若是灰的，需企业管理员在管理后台允许对外分享 |
