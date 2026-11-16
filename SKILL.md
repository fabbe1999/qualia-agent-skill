---
name: qualia
description: "Curate robot datasets before training with Qualia. Upload LeRobot v2.1/v3 folders or ROS 2 MCAP sessions, or import a Hugging Face dataset. Qualia finds the tasks and runs free automatic checks on every episode (frozen commands or joints, jerk, idle, dropped or black frames, joint limits, too short). An optional paid VLM check watches each episode against its task. Keep or reject episodes, trim and split them, save a version, and download it as LeRobot v3, LeRobot v2.1 or MCAP, or as files for Physical Intelligence and Dream Labs. Drives the official qualia CLI with --json output."
version: 3.0.0
metadata:
  openclaw:
    emoji: "🤖"
    homepage: https://docs.qualiastudios.dev
    requires:
      env:
        - QUALIA_API_KEY
      bins:
        - qualia
    primaryEnv: QUALIA_API_KEY
    envVars:
      - name: QUALIA_API_KEY
        required: true
        description: Qualia API key from app.qualiastudios.dev (Settings -> Account -> API keys). Acts as the person who made it. The free checks cost nothing; the VLM check spends the account's credits.
      - name: QUALIA_BASE_URL
        required: false
        description: API origin. Leave unset for production (https://api.qualiastudios.dev). Set it only when your account lives in another Qualia environment.
      - name: HF_TOKEN
        required: false
        description: Only for importing a private or gated Hugging Face dataset. Read from the environment, never passed on the command line.
    install:
      - id: uv
        kind: uv
        package: qualia-cli
        bins:
          - qualia
        label: Install the Qualia CLI (uv)
---

# Qualia

Curate robot data before training: upload, let Qualia check every episode, rule on the episodes, save a version, download it.

## Install and setup

### Install the skill

```bash
openclaw skills install qualia-skill
```

If `@fabbe1999/qualia-skill` or `fabbe1999/qualia-skill` fails, retry with the short slug `qualia-skill`. The skill loads as `qualia`, so its config key is `skills.entries.qualia`. Start a fresh agent turn after installing.

### Install the CLI

The skill drives the official `qualia` CLI (package `qualia-cli`, which brings the Python SDK `qualia-sdk` with it):

```bash
uv tool install qualia-cli
# or
pip install qualia-cli
```

The client and the platform negotiate the upload protocol exactly, so they must be the same generation. If the platform turns the client away as the wrong version, install the exact version the docs name under [Installation](https://docs.qualiastudios.dev/cli/overview.md#installation) and keep that pin.

### Configure the key

1. Sign in at [app.qualiastudios.dev](https://app.qualiastudios.dev).
2. Open **Settings**, then **Account** > **API keys**, click **New key**, then **Create key**. Copy it: it is shown once. Keys expire after 90 days by default.
3. Give it to the agent's environment:

```bash
export QUALIA_API_KEY="your-api-key"
```

For OpenClaw, put it in `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      qualia: {
        enabled: true,
        env: { QUALIA_API_KEY: "your-api-key" }
      }
    }
  }
}
```

When `QUALIA_API_KEY` is set, the CLI ignores its config file, including the stored base URL. Production is the default. For another environment, set `QUALIA_BASE_URL` next to the key.

A key acts as the person who made it, with their role, across the whole organization (or one workspace, if it was made that way). No command needs an account id. Never print, log or echo the key.

## Verify your install

```bash
qualia version              # CLI and SDK versions
qualia auth status          # "API key: configured", the base URL and the key's scope; never prints the key
qualia credit --json        # "balance" is the account's credits: proves the key and the connection
```

## Machine-readable output

Pass `--json` to any command that shows data: stdout then carries JSON only. Parse stdout and branch on the exit code.

| Exit code | Meaning |
|---|---|
| 0 | Success |
| 1 | The command failed or was refused; the reason is on stderr |
| 2 | The command was used wrongly (bad arguments or options) |
| 3 | `dataset upload` only: the bytes are kept, but no episode could be derived |

## When someone asks you to clean up a dataset

Ask for what you need:

- **Where the data is:** a local folder (LeRobot v2.1, LeRobot v3, or ROS 2 MCAP bags, one subfolder per recording), or a Hugging Face dataset plus its exact commit.
- **What the robot should be doing**, if the dataset's task strings don't already say it. Qualia drafts a Task per task string; a person can improve it.
- **What they want out:** which format to download, and whether to keep only clean episodes.

Ask before spending credits or changing many episodes:

- **The VLM check spends credits.** Run `qualia check estimate` first, tell the user the number, and start the run only after they agree.
- **Bulk rulings:** before a `reject` or `keep` with `--filter`, say how many episodes it matches and why.
- **Never delete datasets** unless the user asks for exactly that.

## The path: upload to download

Each step prints JSON with `--json`. `$DATASET` is the dataset id from step 1. Every command also takes the dataset's slug.

### 1. Upload or import

```bash
qualia dataset upload ./session-0412 session-0412 --standalone --json > receipt.json
DATASET=$(jq -r .dataset_id receipt.json)
qualia dataset ingest-report "$DATASET"
```

The format is read from the folder: `meta/info.json` tells LeRobot v2.1 from v3, and any `.mcap` makes it a ROS 2 session. `--source-format lerobot_v2_1|lerobot_v3|mcap_ros2` overrides it. `--standalone` keeps the upload on its own dataset.

From Hugging Face, with the exact 40-character commit (no branch names):

```bash
qualia dataset import-hf your-org/your-dataset <COMMIT_SHA> my-dataset --source-format lerobot_v3 --yes --json
```

Exit 1 does not mean nothing is left: read `qualia dataset uploads` before trying again.

### 2. Wait for preparation and the automatic checks

After an upload, Qualia prepares it on its own: it reads the takes, sorts them into tasks, and links each episode to a Task (a match from the account, or a new draft). It may split a take into pieces. Count on 3 to 8 minutes, sometimes more. Preparation is free.

```bash
qualia check policy "$DATASET"                        # which checks start by themselves
qualia dataset preparation "$DATASET" --wait --timeout 1800 --json   # done when "state" is SUCCEEDED (or FAILED)
qualia check runs --dataset "$DATASET"                # the check runs, newest first
```

When preparation ends, **the free checks** start by themselves (`heuristic: on` by default). Code reads each episode's data, with no model involved. **The paid VLM check**, where a model watches each episode against its Task, starts by itself only where someone switched it on (`graph: off` by default). In `check policy --json`, read `heuristicEnabled` and `graphEnabled`.

A take that preparation split stays listed as the parent, with its pieces as its children. To see the pieces only, filter with `child_count = 0`.

### 3. Read the results

```bash
# every check's last result: how many passed, failed, or could not be judged
# (free checks count episodes; graph.evaluate counts the things it judged in them)
qualia dataset checks list "$DATASET" --json \
  | jq '.datasetChecks[] | {checkId, pass: .lastResult.passCount, fail: .lastResult.failCount, unknown: .lastResult.unknownCount}'

qualia dataset checks findings "$DATASET" -n 1000 --json                          # every check's findings
qualia dataset checks findings "$DATASET" --check heuristic.frozen -n 1000 --json # one check's
qualia dataset issues summary "$DATASET"              # issues and notes per code: open and dismissed
qualia dataset issues list "$DATASET" --filter 'state = OPEN AND blocks = true' -n 100 --json
```

- **The free checks list only their failures.** An episode a check judged without a finding passed it. `unknown` counts the episodes it could not judge.
- **The reason is in each finding's `summary`**, for example which joint a frozen check found stuck and how far its command moved.
- **Notes and issues.** A free check's failure becomes a **note** on the episode: worth reading, not blocking. The VLM check's failures become blocking **issues**. Filters on `open_issue_codes` match blocking issues only; `issues summary` shows both kinds.

### 4. Optional: the VLM check (spends credits)

```bash
EST=$(qualia check estimate "$DATASET" --json | jq -r .credits)
# tell the user $EST, and go on only after they agree
qualia check run "$DATASET" --max-cost "$EST" --wait
qualia dataset checks findings "$DATASET" --check graph.evaluate -n 1000 --json
```

The estimate is a ceiling, not the price. A run reserves it and is charged for what it used; the rest comes back. The balance must cover the ceiling. Until preparation has linked the episodes to Tasks, the estimate says no episode is linked.

### 5. Rule on the episodes

```bash
qualia dataset summary "$DATASET" --facet state --facet open_issue_codes
qualia dataset keep "$DATASET" <EPISODE>... --reason "no open issue"
qualia dataset reject "$DATASET" --filter 'open_issue_codes:"graph_outcome"' --reason "failed the VLM check"
qualia dataset reject "$DATASET" --filter 'metrics.duration_seconds < 2' --reason "too short"
qualia dataset reset "$DATASET" <EPISODE>             # withdraw a ruling
qualia dataset issues dismiss "$DATASET" --filter 'code = "idle_tail"' --reason "fine for this task"
qualia dataset trim <EPISODE> -d "$DATASET" --start 1.5 --end 12
qualia dataset split <EPISODE> -d "$DATASET" --keep 0.5-6 --keep 8-14 --dry-run
```

### 6. Save a version

```bash
qualia dataset version-preview "$DATASET" --json > preview.json
jq '.preview | {episodeCount, unprocessable, sameAsVersion}' preview.json
qualia dataset pin "$DATASET" 1.0 --preview "$(jq -r .preview.name preview.json)" --note "first cut"
```

The preview changes nothing; only `pin` saves the version. By default a version holds the episodes someone kept with `keep` (`kept_by_person`). `--include` picks other classes (`kept`, `flagged`, `rejected`, `rejected_by_person`) and can be repeated. `sameAsVersion` names an existing version with exactly this content.

### 7. Download it for training

```bash
qualia dataset download "${DATASET}:1.0" ./my-dataset-1.0                          # LeRobot v3
qualia dataset download "${DATASET}:1.0" ./my-dataset-1.0 --format lerobot_v2_1
qualia dataset download "${DATASET}:1.0" ./my-dataset-1.0 --format mcap_ros2
qualia dataset download "${DATASET}:1.0" ./for-pi --format pi_mcap_v1               # Physical Intelligence
qualia dataset download "${DATASET}:1.0" ./for-dreamlabs --format dreamlabs_v2_1    # Dream Labs
```

## Find your way around

```bash
qualia dataset list -q shelf --kind all               # datasets by name (20 a page; uploads only without --kind)
qualia dataset episodes "$DATASET" --filter 'operator = "ana"' --json
qualia dataset summary "$DATASET" --facet task --facet operator --facet session
qualia status list --running --json                   # running work; qualia status cancel <name> stops it
qualia activity list --json                           # what people and keys did
```

## When things go wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Every call is refused as unauthenticated | Key missing, expired or revoked, or the wrong environment | `qualia auth status`; with `QUALIA_API_KEY` set, also set `QUALIA_BASE_URL` for a non-production account |
| The platform turns the client away as the wrong version | The CLI is a different generation than the platform | Install the exact version named under Installation in the docs |
| `check estimate` says no episode is linked | Preparation has not ended | `qualia dataset preparation "$DATASET" --wait` |
| A VLM run is refused for credits | The balance is below the run's ceiling | Select fewer episodes with `--filter`, or ask the user to add credits in the dashboard |
| A free check lists no findings | Nothing failed it | Read its `passCount` and `failCount` in `qualia dataset checks list` |
| Steps refused on an upload | The upload was appended to a merged dataset | Run the steps on the merged dataset, or upload with `--standalone` |

## What stays in the dashboard

Signing in, making keys, buying credits (a key can only redeem a voucher), and creating or deleting an organization.

## Training

Training isn't available on plans yet. To request access, write to [support@qualiastudios.dev](mailto:support@qualiastudios.dev).

## Live docs

The commands above are the main path. For every command and option, and for the SDK and REST API:

- Agent guide: [docs.qualiastudios.dev/global/guides/agents.md](https://docs.qualiastudios.dev/global/guides/agents.md)
- Every CLI command: [docs.qualiastudios.dev/cli/commands.md](https://docs.qualiastudios.dev/cli/commands.md)
- Everything in one file: [docs.qualiastudios.dev/llms-full.txt](https://docs.qualiastudios.dev/llms-full.txt)
- Dashboard: [app.qualiastudios.dev](https://app.qualiastudios.dev)
