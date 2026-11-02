#!/usr/bin/env python3
"""在你自己的飞书知识库里建出面试复盘结构。依赖已授权的 lark-cli（用户身份）。
用法: python3 setup_feishu.py --space-id <SPACE_ID> --name 姓名 [--student-id 学号] [--parent <NODE_TOKEN>] [--execute]
默认 dry-run，只打印计划；加 --execute 才真实创建。不放开任何分享权限。"""
import argparse, json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CLI = os.environ.get("LARK_CLI", "lark-cli")

def children(p):
    return [
        ("个人简历在线综合", "docx"), ("个人飞书版简历", "docx"), ("面试表", "bitable"),
        ("面试复盘存档（一次面试一个文档，按模板）", "docx"), ("测试题复盘（一次测试题一个文档）", "docx"),
        ("个人战略（1v1复盘+面试策略）", "docx"), ("个人面试话术文档（自我介绍+打招呼语）", "docx"),
        ("穷尽面试问题汇总（以问题为单位）", "docx"), ("面试经验沉淀（以条为单位）", "docx"),
    ]

def api(method, path, params=None, data=None):
    cmd = [CLI, "api", method, path]
    if params: cmd += ["--params", json.dumps(params, ensure_ascii=False)]
    if data: cmd += ["--data", json.dumps(data, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode: sys.exit(f"API 失败: {method} {path}\n{out.stderr}")
    return json.loads(out.stdout)

def list_nodes(space, parent):
    items, pt = [], None
    while True:
        q = {"page_size": 50}
        if parent: q["parent_node_token"] = parent
        if pt: q["page_token"] = pt
        d = api("GET", f"/open-apis/wiki/v2/spaces/{space}/nodes", q)["data"]
        items += d.get("items", [])
        if not d.get("has_more"): return items
        pt = d["page_token"]

def ensure(space, parent, title, typ, dry, existing_cache):
    if not dry:
        for n in list_nodes(space, parent):
            if n["title"] == title:
                print(f"  跳过（已存在）: {title}"); return n
    if dry:
        print(f"  [计划] 新建 {typ:8s} {title}"); return {"node_token": f"<{title}>", "obj_token": None}
    body = {"obj_type": typ, "node_type": "origin", "title": title}
    if parent: body["parent_node_token"] = parent
    n = api("POST", f"/open-apis/wiki/v2/spaces/{space}/nodes", data=body)["data"]["node"]
    print(f"  已建: {title} -> {n['node_token']}"); return n

def setup_fields(app_token, dry):
    spec = json.load(open(os.path.join(ROOT, "templates", "面试表Bitable字段定义.json"), encoding="utf-8"))
    print(f"  [面试表字段] {len(spec['fields'])} 个: " + "、".join(f["field_name"] for f in spec["fields"]))
    if dry: return
    tbl = api("GET", f"/open-apis/bitable/v1/apps/{app_token}/tables")["data"]["items"][0]["table_id"]
    base = f"/open-apis/bitable/v1/apps/{app_token}/tables/{tbl}/fields"
    have = {f["field_name"]: f for f in api("GET", base, {"page_size": 100})["data"]["items"]}
    for f in spec["fields"]:
        if f["field_name"] in have: continue
        if f.get("primary"):
            pk = next(x for x in have.values() if x.get("is_primary"))
            api("PUT", f"{base}/{pk['field_id']}", data={"field_name": f["field_name"], "type": 1}); continue
        body = {"field_name": f["field_name"], "type": f["type"]}
        if "options" in f: body["property"] = {"options": [{"name": o} for o in f["options"]]}
        if f["type"] == 18: body["property"] = {"table_id": tbl, "multiple": False}
        api("POST", base, data=body)

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--space-id", required=True); a.add_argument("--name", required=True)
    a.add_argument("--student-id", default=""); a.add_argument("--parent", default="")
    a.add_argument("--execute", action="store_true"); a.add_argument("--dry-run", action="store_true")
    o = a.parse_args(); dry = not o.execute or o.dry_run
    P = f"{o.student_id}-{o.name}" if o.student_id else o.name
    print(f"{'DRY-RUN' if dry else 'EXECUTE'} space={o.space_id} 前缀={P}")
    root = ensure(o.space_id, o.parent or None, f"{P}-个人面试记录表&复盘", "docx", dry, None)
    made = {}
    for t, typ in children(P):
        made[t] = ensure(o.space_id, root["node_token"], f"{P}-{t}", typ, dry, None)
    setup_fields(made["面试表"].get("obj_token"), dry)
    arch = made["面试复盘存档（一次面试一个文档，按模板）"]
    ensure(o.space_id, arch["node_token"], "复盘模板", "docx", dry, None)
    print("  [计划] 复盘模板写入 templates/复盘文档模板.md（建议: lark-cli docs +update，markdown 覆盖，仅一次）")
    print("  [计划] 总入口写入子文档链接 + 规则（一个入口/一岗一行/一场一档/测试题一题一档/问题只记问题/经验以条为单位）")
    print("  [计划] 回读核对节点与字段；输出链接清单")
    print("  [提醒] 不自动放开权限：检查脱敏后由你本人设为「互联网获得链接的人可编辑（含子页面）」")
    if not dry:
        for n in [root] + list_nodes(o.space_id, root["node_token"]):
            print(f"  {n['title']}\t{n['obj_type']}\thttps://<你的域名>.feishu.cn/wiki/{n['node_token']}")

if __name__ == "__main__":
    main()
