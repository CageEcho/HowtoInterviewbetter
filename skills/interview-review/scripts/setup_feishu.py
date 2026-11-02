#!/usr/bin/env python3
"""在你自己的飞书知识库里建出「面试复盘」结构，并给每个页面写好说明框、建设攻略和（示例）内容。
依赖已授权的 lark-cli（用户身份）。
用法: python3 setup_feishu.py --space-id <SPACE_ID> --name 姓名 [--student-id 学号] [--parent <NODE_TOKEN>] [--no-examples] [--execute]
默认 dry-run，只打印计划；加 --execute 才真实创建。可重复执行：同名节点跳过，已有正文的文档不覆盖。不放开任何分享权限。"""
import argparse, json, os, subprocess, sys, tempfile, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
XML = os.path.join(ROOT, "templates", "feishu")
CLI = os.environ.get("LARK_CLI", "lark-cli")

# (key, 标题后缀, 类型, 内容文件, 父key)   标题: 前缀P + "-" + 后缀；后缀以 "!" 开头表示不加前缀
NODES = [
    ("resume_all", "个人简历在线综合", "docx", "01-个人简历在线综合.xml", "root"),
    ("resume", "个人飞书版简历", "docx", "02-个人飞书版简历.xml", "root"),
    ("method", "简历+打招呼语+面试 详细方法论", "docx", "10-简历打招呼语面试方法论.xml", "root"),
    ("table", "面试表", "bitable", None, "root"),
    ("archive", "面试复盘存档（一次面试一个文档，按模板）", "docx", "03-面试复盘存档.xml", "root"),
    ("tpl", "!复盘模板", "docx", "03a-复盘模板.xml", "archive"),
    ("weekly", "周总文档（每周汇总）", "docx", "03b-周总文档.xml", "archive"),
    ("case", "!（案例）某软件公司（二面）-AI 产品经理", "docx", "03c-案例复盘.xml", "archive"),
    ("score", "打分表", "docx", "04-打分表.xml", "root"),
    ("test", "测试题复盘（一次测试题一个文档）", "docx", "05-测试题复盘.xml", "root"),
    ("testcase", "!（案例）某大厂AI助手（一面）-竞品分析测试题", "docx", "05a-案例测试题.xml", "test"),
    ("strategy", "个人战略（1v1复盘+面试策略）", "docx", "06-个人战略.xml", "root"),
    ("script", "个人面试话术文档（自我介绍+打招呼语）", "docx", "07-个人面试话术文档.xml", "root"),
    ("questions", "穷尽面试问题汇总（以问题为单位）", "docx", "08-穷尽面试问题汇总.xml", "root"),
    ("exp", "面试经验沉淀（以条为单位）", "docx", "09-面试经验沉淀.xml", "root"),
]
EXAMPLE_KEYS = {"case", "testcase"}
LINK_LABEL = {"resume_all": "个人简历在线综合", "resume": "个人飞书版简历", "method": "简历+打招呼语+面试 详细方法论",
              "table": "面试表（多维表格，一岗一行）", "archive": "面试复盘存档", "tpl": "复盘模板", "weekly": "周总文档",
              "score": "打分表", "test": "测试题复盘", "strategy": "个人战略", "script": "个人面试话术文档",
              "questions": "穷尽面试问题汇总", "exp": "面试经验沉淀"}

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def api(method, path, params=None, data=None, soft=False):
    cmd = [CLI, "api", method, path]
    if params: cmd += ["--params", json.dumps(params, ensure_ascii=False)]
    if data is not None: cmd += ["--data", json.dumps(data, ensure_ascii=False)]
    out = run(cmd)
    if out.returncode:
        if soft: print(f"  [警告] {method} {path}: {(out.stderr or out.stdout)[:200]}"); return {}
        sys.exit(f"API 失败: {method} {path}\n{out.stderr}{out.stdout}")
    return json.loads(out.stdout or "{}")

def list_nodes(space, parent):
    items, pt = [], None
    while True:
        q = {"page_size": 50}
        if parent: q["parent_node_token"] = parent
        if pt: q["page_token"] = pt
        d = api("GET", f"/open-apis/wiki/v2/spaces/{space}/nodes", q)["data"]
        items += d.get("items", []) or []
        if not d.get("has_more"): return items
        pt = d["page_token"]

def ensure(space, parent, title, typ, dry):
    """返回 (node, 是否新建)。同名节点直接复用。"""
    if dry:
        print(f"  [计划] 新建 {typ:8s} {title}"); return {"node_token": f"<{title}>", "obj_token": None}, True
    for n in list_nodes(space, parent):
        if n["title"] == title:
            print(f"  跳过（已存在）: {title}"); return n, False
    body = {"obj_type": typ, "node_type": "origin", "title": title}
    if parent: body["parent_node_token"] = parent
    n = api("POST", f"/open-apis/wiki/v2/spaces/{space}/nodes", data=body)["data"]["node"]
    print(f"  已建: {title} -> {n['node_token']}"); return n, True

def write_xml(node, xml_text, label, dry):
    """用飞书 XML 覆盖写入（保留 <title>，彩色高亮框不丢）。只对本次新建的文档执行。"""
    if dry:
        print(f"  [计划] 写入内容: {label}（{xml_text.count('<callout')} 个高亮框）"); return
    with tempfile.NamedTemporaryFile("w", suffix=".xml", dir=".", delete=False, encoding="utf-8") as f:
        f.write(xml_text); tmp = os.path.basename(f.name)
    try:
        r = run([CLI, "docs", "+update", "--doc", node["obj_token"], "--command", "overwrite",
                 "--doc-format", "xml", "--content", "@" + tmp])
    finally:
        os.remove(tmp)
    if r.returncode: print(f"  [警告] 写入失败 {label}: {(r.stderr or r.stdout)[:300]}")
    else: print(f"  已写入内容: {label}")

def load(fname, P):
    return open(os.path.join(XML, fname), encoding="utf-8").read().replace("{P}", esc(P))

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def setup_table(app_token, dry, examples):
    spec = json.load(open(os.path.join(ROOT, "templates", "面试表Bitable字段定义.json"), encoding="utf-8"))
    print(f"  [面试表字段] {len(spec['fields'])} 个: " + "、".join(f["field_name"] for f in spec["fields"]))
    ex = spec.get("example_records", []) if examples else []
    print(f"  [面试表] 删除默认列（单选/日期/附件等）与默认空行；写入 {len(ex)} 行（示例）记录")
    if dry: return
    tbl = api("GET", f"/open-apis/bitable/v1/apps/{app_token}/tables")["data"]["items"][0]["table_id"]
    base = f"/open-apis/bitable/v1/apps/{app_token}/tables/{tbl}"
    have = {f["field_name"]: f for f in api("GET", f"{base}/fields", {"page_size": 100})["data"]["items"]}
    wanted = {f["field_name"] for f in spec["fields"]}
    for f in spec["fields"]:
        if f["field_name"] in have: continue
        if f.get("primary"):
            pk = next(x for x in have.values() if x.get("is_primary"))
            api("PUT", f"{base}/fields/{pk['field_id']}", data={"field_name": f["field_name"], "type": 1})
            have[f["field_name"]] = pk; have.pop(pk["field_name"], None); continue
        body = {"field_name": f["field_name"], "type": f["type"]}
        if "options" in f: body["property"] = {"options": [{"name": o} for o in f["options"]]}
        if f["type"] == 18: body["property"] = {"table_id": tbl, "multiple": False}
        api("POST", f"{base}/fields", data=body)
    # 删除新建表自带的默认列
    for f in api("GET", f"{base}/fields", {"page_size": 100})["data"]["items"]:
        if f["field_name"] not in wanted and not f.get("is_primary"):
            api("DELETE", f"{base}/fields/{f['field_id']}", soft=True); print(f"  已删默认列: {f['field_name']}")
    # 删除默认空行
    recs = (api("GET", f"{base}/records", {"page_size": 100}, soft=True).get("data") or {}).get("items") or []
    empty = [r["record_id"] for r in recs if not any(v not in (None, "", []) for v in (r.get("fields") or {}).values())]
    if empty:
        api("POST", f"{base}/records/batch_delete", data={"records": empty}, soft=True); print(f"  已删默认空行: {len(empty)}")
    if ex:
        now = int(time.time() * 1000)
        rows = []
        for r in ex:
            fields = {}
            for k, v in r.items():
                if isinstance(v, dict) and "days_from_now" in v: v = now + v["days_from_now"] * 86400000
                fields[k] = v
            rows.append({"fields": fields})
        api("POST", f"{base}/records/batch_create", data={"records": rows}, soft=True); print(f"  已写入示例行: {len(rows)}")

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--space-id", required=True); a.add_argument("--name", required=True)
    a.add_argument("--student-id", default=""); a.add_argument("--parent", default="")
    a.add_argument("--root-title", default="", help="自定义总入口标题（默认 P-个人面试记录表&复盘）")
    a.add_argument("--no-examples", action="store_true", help="不建（案例）子文档、不写示例行")
    a.add_argument("--overwrite", action="store_true", help="对已存在的同名文档也覆盖写入（慎用，只用于修复自己刚建的空页面）")
    a.add_argument("--execute", action="store_true"); a.add_argument("--dry-run", action="store_true")
    o = a.parse_args(); dry = not o.execute or o.dry_run; examples = not o.no_examples
    P = f"{o.student_id}-{o.name}" if o.student_id else o.name
    print(f"{'DRY-RUN' if dry else 'EXECUTE'} space={o.space_id} 前缀={P}")
    root_title = o.root_title or f"{P}-个人面试记录表&复盘"
    root, root_new = ensure(o.space_id, o.parent or None, root_title, "docx", dry)
    made, new = {"root": root}, {"root": root_new}
    for key, suffix, typ, fname, parent in NODES:
        if key in EXAMPLE_KEYS and not examples: continue
        title = suffix[1:] if suffix.startswith("!") else f"{P}-{suffix}"
        made[key], new[key] = ensure(o.space_id, made[parent]["node_token"], title, typ, dry)
    if new["table"] or o.overwrite: setup_table(made["table"].get("obj_token"), dry, examples)
    for key, suffix, typ, fname, parent in NODES:
        if not fname or key not in made: continue
        if new[key] or o.overwrite: write_xml(made[key], load(fname, P), fname, dry)
        else: print(f"  跳过写入（文档已存在，不覆盖）: {fname}")
    # 总入口：目录用 @文档 引用，不依赖域名
    items = []
    for key in ["resume_all", "resume", "method", "table", "archive", "tpl", "weekly", "score", "test",
                "strategy", "script", "questions", "exp"]:
        tok = made[key].get("obj_token") or "OBJ_TOKEN"
        items.append(f'<li>{LINK_LABEL[key]}：<cite type="doc" doc-id="{tok}"/></li>')
    hub = load("00-总入口.xml", P).replace("{LINKS}", "<ul>" + "".join(items) + "</ul>")
    hub = hub.replace(f"<title>{esc(P)}-个人面试记录表&amp;复盘</title>", f"<title>{esc(root_title)}</title>")
    if root_new or o.overwrite: write_xml(root, hub, "00-总入口.xml", dry)
    else: print("  跳过写入（总入口已存在，不覆盖）")
    print("  [提醒] 不自动放开权限：检查脱敏后由你本人设为「互联网获得链接的人可阅读/编辑（含子页面）」")
    print("  [提醒] 每个页面的（示例）区块照着改成自己的内容后即可删除；（案例）子文档可保留作参照")
    if not dry:
        arch, test = made["archive"]["node_token"], made["test"]["node_token"]
        for n in [root] + list_nodes(o.space_id, root["node_token"]) + list_nodes(o.space_id, arch) + list_nodes(o.space_id, test):
            print(f"  {n['title']}\t{n['obj_type']}\thttps://<你的域名>.feishu.cn/wiki/{n['node_token']}")

if __name__ == "__main__":
    main()
