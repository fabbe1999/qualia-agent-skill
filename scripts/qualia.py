#!/usr/bin/env python3
"""Qualia CLI — VLA fine-tuning platform.

Pure Python, no external dependencies. Requires Python 3.6+.
Set QUALIA_API_KEY environment variable before use.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.qualiastudios.dev"


def get_api_key():
    key = os.environ.get("QUALIA_API_KEY", "")
    if not key:
        print("Error: QUALIA_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(method, path, body=None):
    """Make an authenticated API request. Returns parsed JSON."""
    url = f"{API_BASE}{path}"
    headers = {"X-API-Key": get_api_key()}
    data = None

    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            print(f"API error ({e.code}): {json.dumps(err_body, indent=2)}", file=sys.stderr)
        except Exception:
            print(f"API error ({e.code}): {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ── Commands ──────────────────────────────────────────────────────────


def cmd_credits(_args):
    result = api_request("GET", "/v1/credits")
    print(f"Credits: {result.get('balance', 'unknown')}")


def cmd_models(_args):
    result = api_request("GET", "/v1/models")
    for m in result.get("data", []):
        slots = ", ".join(m.get("camera_slots", []))
        print(f"[{m['id']}] {m['name']}")
        print(f"  {m.get('description', '')}")
        print(f"  camera slots: {slots}")
        if m.get("base_model_id"):
            print(f"  base model: {m['base_model_id']}")
        if m.get("supports_custom_model") is False:
            print("  ⚠ custom model_id not supported")
        print()


def cmd_instances(_args):
    result = api_request("GET", "/v1/instances")
    for i in result.get("data", []):
        specs = i.get("specs", {})
        regions = ", ".join(r["name"] for r in i.get("regions", []))
        print(f"[{i['id']}] {i['gpu_description']} — {i['credits_per_hour']} credits/hr")
        print(f"  {specs.get('gpu_count', '?')}x {specs.get('gpu_type', '?')} | "
              f"{specs.get('memory_gib', '?')}GB RAM | "
              f"{specs.get('storage_gib', '?')}GB storage | "
              f"{specs.get('vcpus', '?')} vCPUs")
        print(f"  regions: {regions}")
        print()


def cmd_projects(_args):
    result = api_request("GET", "/v1/projects")
    for p in result.get("data", []):
        desc = f" — {p['description']}" if p.get("description") else ""
        created = p.get("created_at", "")[:10]
        jobs = p.get("jobs", [])
        print(f"[{p['project_id']}] {p['name']}{desc}")
        print(f"  created: {created} | jobs: {len(jobs)}")
        for j in jobs:
            status = j.get("status", "unknown")
            name = j.get("name") or j.get("model") or ""
            dataset = f" on {j['dataset']}" if j.get("dataset") else ""
            print(f"  · {j['job_id']} [{status}] {name}{dataset}")
        print()


def cmd_project_create(args):
    if not args:
        print("Usage: qualia.py project-create <name> [description]", file=sys.stderr)
        sys.exit(1)
    body = {"name": args[0]}
    if len(args) > 1 and args[1]:
        body["description"] = args[1]
    result = api_request("POST", "/v1/projects", body)
    if result.get("created"):
        print(f"Created project: {result['project_id']}")
    else:
        print("Failed to create project")


def cmd_project_delete(args):
    if not args:
        print("Usage: qualia.py project-delete <project_id>", file=sys.stderr)
        sys.exit(1)
    result = api_request("DELETE", f"/v1/projects/{args[0]}")
    if result.get("deleted"):
        print(f"Deleted project: {result['project_id']}")
    else:
        print("Failed to delete project")


def cmd_dataset_keys(args):
    if not args:
        print("Usage: qualia.py dataset-keys <huggingface_dataset_id>", file=sys.stderr)
        print("  e.g. qualia.py dataset-keys lerobot/aloha_sim_insertion_human", file=sys.stderr)
        sys.exit(1)
    dataset_id = args[0]
    result = api_request("GET", f"/v1/datasets/{dataset_id}/image-keys")
    print(f"Image keys for {dataset_id}:")
    for key in result.get("image_keys", []):
        print(f"  {key}")


def cmd_hyperparams(args):
    if not args:
        print("Usage: qualia.py hyperparams <act|smolvla|pi0|pi05|gr00t_n1_5> [model_id]", file=sys.stderr)
        print("  model_id required for: smolvla, pi0, pi05", file=sys.stderr)
        sys.exit(1)
    vla_type = args[0]
    model_id = args[1] if len(args) > 1 else None
    path = f"/v1/finetune/hyperparams/defaults?vla_type={urllib.parse.quote(vla_type)}"
    if model_id:
        path += f"&model_id={urllib.parse.quote(model_id)}"
    result = api_request("GET", path)
    label = f"{vla_type} ({model_id})" if model_id else vla_type
    print(f"Defaults for {label}:")
    print(json.dumps(result.get("data", result), indent=2))


def cmd_hyperparams_validate(args):
    if len(args) < 2:
        print("Usage: qualia.py hyperparams-validate <vla_type> '<hyperparams_json>'", file=sys.stderr)
        sys.exit(1)
    vla_type = args[0]
    try:
        hyper_json = json.loads(args[1])
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    path = f"/v1/finetune/hyperparams/validate?vla_type={urllib.parse.quote(vla_type)}"
    result = api_request("POST", path, hyper_json)
    if result.get("valid"):
        print("✓ Valid")
    elif "valid" in result and not result["valid"]:
        print("✗ Invalid")
        for issue in result.get("issues", []):
            print(f"  · {issue.get('field', '?')}: {issue.get('message', '')}")
    else:
        print(json.dumps(result, indent=2))


def _parse_flags(argv):
    """Parse --key value and --key=value flags from argv. Returns dict."""
    flags = {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            if "=" in arg:
                key, val = arg.split("=", 1)
                flags[key[2:]] = val
            elif i + 1 < len(argv):
                flags[arg[2:]] = argv[i + 1]
                i += 1
            else:
                print(f"Flag {arg} requires a value", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(1)
        i += 1
    return flags


def cmd_finetune(args):
    if len(args) < 5:
        print("Usage: qualia.py finetune <project_id> <vla_type> <dataset_id> <hours> '<camera_mappings_json>' [flags]", file=sys.stderr)
        print(file=sys.stderr)
        print("  Required:", file=sys.stderr)
        print("    project_id       UUID from 'qualia.py projects'", file=sys.stderr)
        print("    vla_type         act | smolvla | pi0 | pi05 | gr00t_n1_5", file=sys.stderr)
        print("    dataset_id       HuggingFace dataset ID (e.g. lerobot/pusht)", file=sys.stderr)
        print("    hours            Training duration (max 168)", file=sys.stderr)
        print("    camera_mappings  JSON: slot name → dataset image key", file=sys.stderr)
        print('                     e.g. \'{"cam_1": "observation.images.top"}\'', file=sys.stderr)
        print(file=sys.stderr)
        print("  Optional flags:", file=sys.stderr)
        print("    --model <id>         Base model (required for smolvla/pi0/pi05)", file=sys.stderr)
        print("    --name <str>         Job display name", file=sys.stderr)
        print("    --instance <id>      GPU instance (from 'qualia.py instances')", file=sys.stderr)
        print("    --region <name>      Cloud region", file=sys.stderr)
        print("    --batch-size <n>     Training batch size (1-512, default 32)", file=sys.stderr)
        print("    --hyper-spec '<json>' Advanced hyperparameters (from 'qualia.py hyperparams')", file=sys.stderr)
        print("    --rabc <model_path>  Enable RA-BC with SARM reward model (HF path)", file=sys.stderr)
        print("    --rabc-image-key <k> Image key for reward annotations", file=sys.stderr)
        print("    --rabc-head-mode <m> RA-BC head mode (e.g. sparse)", file=sys.stderr)
        print(file=sys.stderr)
        print("  Tip: run 'qualia.py dataset-keys <dataset_id>' to discover image key names", file=sys.stderr)
        sys.exit(1)

    project_id, vla_type, dataset_id = args[0], args[1], args[2]

    try:
        hours = int(args[3]) if "." not in args[3] else float(args[3])
    except ValueError:
        print(f"Invalid hours value: {args[3]}", file=sys.stderr)
        sys.exit(1)

    try:
        camera_mappings = json.loads(args[4])
    except json.JSONDecodeError as e:
        print(f"Invalid camera_mappings JSON: {e}", file=sys.stderr)
        sys.exit(1)

    flags = _parse_flags(args[5:])

    body = {
        "project_id": project_id,
        "vla_type": vla_type,
        "dataset_id": dataset_id,
        "hours": hours,
        "camera_mappings": camera_mappings,
    }

    if "model" in flags:
        body["model_id"] = flags["model"]
    if "name" in flags:
        body["name"] = flags["name"]
    if "instance" in flags:
        body["instance_type"] = flags["instance"]
    if "region" in flags:
        body["region"] = flags["region"]
    if "batch-size" in flags:
        try:
            body["batch_size"] = int(flags["batch-size"])
        except ValueError:
            print(f"Invalid batch-size: {flags['batch-size']}", file=sys.stderr)
            sys.exit(1)
    if "hyper-spec" in flags:
        try:
            body["vla_hyper_spec"] = json.loads(flags["hyper-spec"])
        except json.JSONDecodeError as e:
            print(f"Invalid hyper-spec JSON: {e}", file=sys.stderr)
            sys.exit(1)
    if "rabc" in flags:
        body["use_rabc"] = True
        body["sarm_reward_model_path"] = flags["rabc"]
        if "rabc-image-key" in flags:
            body["sarm_image_observation_key"] = flags["rabc-image-key"]
        if "rabc-head-mode" in flags:
            body["rabc_head_mode"] = flags["rabc-head-mode"]

    result = api_request("POST", "/v1/finetune", body)
    print(f"Job created: {result.get('job_id', 'unknown')}")
    print(f"Status: {result.get('status', 'unknown')}")
    if result.get("message"):
        print(f"Message: {result['message']}")


def cmd_status(args):
    if not args:
        print("Usage: qualia.py status <job_id>", file=sys.stderr)
        sys.exit(1)
    result = api_request("GET", f"/v1/finetune/{args[0]}")
    print(f"Job {result.get('job_id', '?')}")
    print(f"Status: {result.get('status', '?')} | Phase: {result.get('current_phase', '?')}")
    print()
    for phase in result.get("phases", []):
        status_str = phase.get("status", "?").upper()
        name = phase.get("name", "?")
        started = ""
        if phase.get("started_at"):
            started = f" (started {phase['started_at'][:10]})"
        print(f"[{status_str}] {name}{started}")
        if phase.get("error"):
            print(f"  Error: {phase['error']}")
        for event in phase.get("events", []):
            ev_status = event.get("status", "?")
            ev_msg = event.get("message", "")
            ev_err = f" | {event['error']}" if event.get("error") else ""
            ev_retry = f" (retry {event['retry_attempt']})" if event.get("retry_attempt", 0) > 0 else ""
            print(f"  → [{ev_status}] {ev_msg}{ev_err}{ev_retry}")


def cmd_cancel(args):
    if not args:
        print("Usage: qualia.py cancel <job_id>", file=sys.stderr)
        sys.exit(1)
    result = api_request("POST", f"/v1/finetune/{args[0]}/cancel")
    status = "cancelled" if result.get("cancelled") else "cancellation failed"
    msg = f" — {result['message']}" if result.get("message") else ""
    print(f"Job {result.get('job_id', '?')}: {status}{msg}")


def cmd_help(_args):
    print("Qualia CLI - VLA fine-tuning platform")
    print()
    print("Commands:")
    print("  credits                                    Check credit balance")
    print("  models                                     List VLA types, camera slots, base models")
    print("  instances                                  List GPU instances with specs and pricing")
    print()
    print("  projects                                   List projects with jobs")
    print("  project-create <name> [description]        Create a project")
    print("  project-delete <project_id>                Delete a project (no active jobs)")
    print()
    print("  dataset-keys <dataset_id>                  List image keys in a HuggingFace dataset")
    print("  hyperparams <vla_type> [model_id]          Get default hyperparameters")
    print("  hyperparams-validate <vla_type> '<json>'   Validate custom hyperparameters")
    print()
    print("  finetune <project_id> <vla_type> <dataset_id> <hours> '<cameras>' [--flags]")
    print("    --model <id>         Base model ID (required for smolvla/pi0/pi05)")
    print("    --name <str>         Job display name")
    print("    --instance <id>      GPU instance type")
    print("    --region <name>      Cloud region")
    print("    --batch-size <n>     Batch size (1-512)")
    print("    --hyper-spec '<json>' Custom hyperparameters")
    print("    --rabc <model_path>  Enable RA-BC with SARM reward model (HF path)")
    print("    --rabc-image-key <k> Image key for reward annotations")
    print("    --rabc-head-mode <m> RA-BC head mode (e.g. sparse)")
    print()
    print("  status <job_id>                            Check job status and phase history")
    print("  cancel <job_id>                            Cancel a running job")
    print()
    print("VLA types: act, smolvla, pi0, pi05, gr00t_n1_5, sarm")
    print("  model_id REQUIRED for: smolvla, pi0, pi05")
    print("  model_id NOT supported for: act, gr00t_n1_5, sarm")
    print("  RA-BC supported for: smolvla, pi0, pi05")


COMMANDS = {
    "credits": cmd_credits,
    "models": cmd_models,
    "instances": cmd_instances,
    "projects": cmd_projects,
    "project-create": cmd_project_create,
    "project-delete": cmd_project_delete,
    "dataset-keys": cmd_dataset_keys,
    "hyperparams": cmd_hyperparams,
    "hyperparams-validate": cmd_hyperparams_validate,
    "finetune": cmd_finetune,
    "status": cmd_status,
    "cancel": cmd_cancel,
    "help": cmd_help,
}


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "help"
    rest = args[1:] if len(args) > 1 else []

    handler = COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print("Run 'qualia.py help' for available commands.", file=sys.stderr)
        sys.exit(1)

    handler(rest)


if __name__ == "__main__":
    main()
