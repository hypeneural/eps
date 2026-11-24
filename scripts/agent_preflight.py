"""Offline project-local Antigravity configuration check; not a runtime discovery test."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1]
BASE_SKILLS={"eps-first-test","eps-tp40-engineering","eps-historical-review","eps-render-quality","eps-package-audit","eps-audit","eps-resume"}
TOOLS={"view_file","grep_search","replace_file_content","run_command"}
RULES={"always_on","model_decision","glob","manual"}

def metadata(path):
    body=path.read_text(encoding="utf-8")
    parts=body.split("---",2)
    if len(parts)!=3 or parts[0].strip() or not parts[1].startswith("\n") or not parts[2].strip():
        raise ValueError(f"{path}: frontmatter/body required")
    value=yaml.safe_load(parts[1])
    if not isinstance(value,dict):
        raise ValueError(f"{path}: invalid frontmatter")
    return value

def inspect(root):
    root=Path(root)
    errors=[]
    skills={}
    agents={}
    rules={}
    def issue(path,reason):
        errors.append(f"{path.relative_to(root)}: {reason}")
    for path in sorted((root/".agents/skills").glob("*/SKILL.md")):
        try:
            m=metadata(path); name=m.get("name",path.parent.name)
            if name!=path.parent.name or not re.fullmatch("[a-z0-9-]+",name) or name in skills or not isinstance(m.get("description"),str) or not m["description"].strip():
                raise ValueError("invalid or duplicate skill metadata")
            skills[name]=str(path.relative_to(root))
        except (ValueError,TypeError,yaml.YAMLError) as exc:
            issue(path,str(exc))
    for path in sorted((root/".agents/agents").glob("*.md"))+sorted((root/".agents/agents").glob("*/agent.md")):
        try:
            m=metadata(path); name=m.get("name")
            if not isinstance(name,str) or not re.fullmatch("[a-z0-9-]+",name) or name in agents or not isinstance(m.get("description"),str) or not m["description"].strip():
                raise ValueError("invalid or duplicate agent metadata")
            tools=m.get("tools",[])
            if not isinstance(tools,list) or any(not isinstance(x,str) or x not in TOOLS for x in tools):
                raise ValueError("tool outside project-reviewed allowlist")
            if m.get("commandExecutionPolicy")!="sandbox" or m.get("model","inherit") not in ("inherit","flash","pro"):
                raise ValueError("agent policy or model invalid")
            if any(type(m.get(k)) is not bool for k in ("mainAgent","subagent")):
                raise ValueError("explicit boolean agent roles required")
            if m.get("skills") or m.get("plugins") or m.get("mcpServers"):
                raise ValueError("project uses on-demand skills and no agent-specific plugins/MCP")
            agents[name]=str(path.relative_to(root))
        except (ValueError,TypeError,yaml.YAMLError) as exc:
            issue(path,str(exc))
    for path in sorted((root/".agents/rules").glob("*.md")):
        try:
            m=metadata(path); trigger=m.get("trigger")
            if trigger not in RULES or (trigger=="model_decision" and not m.get("description")) or (trigger=="glob" and not (m.get("glob") or m.get("globs"))):
                raise ValueError("invalid rule trigger or missing activation metadata")
            rules[path.stem]=trigger
        except (ValueError,TypeError,yaml.YAMLError) as exc:
            issue(path,str(exc))
    has_portal=(root/"portal/templates/index.html").is_file()
    expected=BASE_SKILLS|({"eps-publish-model"} if has_portal else set())
    expected_agents={"eps-engineer","eps-reviewer"}|({"eps-portal"} if has_portal else set())
    for missing in sorted(expected-set(skills)):
        errors.append("Missing skill: "+missing)
    for missing in sorted(expected_agents-set(agents)):
        errors.append("Missing agent: "+missing)
    required=["AGENTS.md","README.md","docs/18_GUIA_AGENTE.md","docs/19_WORKFLOWS_AGENTE.md","scripts/prepare_tp40.py","scripts/new_tp40.py","scripts/first_test.py","scripts/render_quality.py","scripts/verify_package.py","scripts/review_historical_roof.py"]
    if has_portal:
        required+=["docs/17_PORTAL_ISONUNES.md","scripts/build_gallery.py","scripts/check_gallery_browser.py","scripts/check_gallery_live.py","scripts/deploy_gallery.py"]
    for path in required:
        if not (root/path).is_file():
            errors.append("Missing required path: "+path)
    if (root/"AGENTS.md").is_file() and (root/"AGENTS.md").read_text(encoding="utf-8").startswith("---"):
        errors.append("Root AGENTS.md must not use frontmatter")
    if "eps-delivery" not in rules or (has_portal and "eps-portal" not in rules):
        errors.append("Missing required modular rule")
    return {"portal":has_portal,"skills":skills,"agents":agents,"rules":rules,"errors":errors}

def git(root,*args):
    p=subprocess.run(["git",*args],cwd=root,capture_output=True,text=True,check=False)
    return p.stdout.strip() if p.returncode==0 else None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    result=inspect(ROOT)
    result.update(branch=git(ROOT,"branch","--show-current"),head=git(ROOT,"rev-parse","HEAD"),dirty=bool(git(ROOT,"status","--porcelain")),python=sys.version.split()[0])
    if args.json:
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(f"Branch: {result['branch']} | HEAD: {result['head']} | Python: {result['python']}")
        print(f"Skills: {len(result['skills'])} | Agents: {len(result['agents'])} | Rules: {len(result['rules'])} | Portal: {result['portal']} | Dirty: {result['dirty']}")
        for error in result["errors"]:
            print("ERROR:",error)
        print("Local structure OK; runtime discovery still requires Antigravity." if not result["errors"] else "Configuration invalid.")
    return int(bool(result["errors"]))
if __name__=="__main__":
    raise SystemExit(main())
