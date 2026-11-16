# Qualia Agent Skill 🤖🦾

Give your AI agent a robot-data curation skill. With [Qualia](https://qualiastudios.dev), an agent uploads robot recordings, lets Qualia check every episode, keeps the good ones, and downloads a clean version ready for training.

## What can your agent do with this?

- Upload LeRobot v2.1 / v3 folders or ROS 2 MCAP sessions, or import a Hugging Face dataset at an exact commit
- Let Qualia find the tasks in the data and link each episode to a Task
- Read the free automatic checks on every episode: frozen commands or joints, jerk, idle, dropped or black frames, joint limits, episodes that are too short
- Run the optional VLM check, where a model watches each episode against its task (paid in credits, always estimated first)
- Keep or reject episodes, trim and split them, and dismiss issues that don't matter for the task
- Save a version and download it as LeRobot v3, LeRobot v2.1, MCAP, or as files for Physical Intelligence and Dream Labs

## Built for agents

The skill drives the official [`qualia` CLI](https://docs.qualiastudios.dev/cli/overview.md). Every command that shows data takes `--json`, so stdout carries JSON only. A failed command exits 1 with the reason on stderr, and a command used wrongly exits 2. `SKILL.md` walks the agent through the whole path, from upload to download, and says when to ask the user first (before spending credits, before bulk rulings).

## Setup

### 1. Install the skill

```bash
openclaw skills install qualia-skill
```

Current OpenClaw installers may **not** accept owner-qualified slugs such as `@fabbe1999/qualia-skill` or `fabbe1999/qualia-skill`. If either fails, use the short slug above.

Manual install is also fine:

```bash
mkdir -p ~/.openclaw/workspace/skills
git clone https://github.com/fabbe1999/qualia-agent-skill ~/.openclaw/workspace/skills/qualia-skill
```

### 2. Install the Qualia CLI

```bash
uv tool install qualia-cli
# or
pip install qualia-cli
```

The CLI and the platform must be the same generation. If the platform turns the client away as the wrong version, install the exact version named under [Installation](https://docs.qualiastudios.dev/cli/overview.md#installation).

### 3. Configure the API key

Make a key in the [Qualia app](https://app.qualiastudios.dev): **Settings** > **Account** > **API keys** > **New key**.

For a shell session:

```bash
export QUALIA_API_KEY="your-api-key"
```

For OpenClaw, add it under `skills.entries.qualia.env` in `~/.openclaw/openclaw.json`:

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

Keep the key out of prompts, screenshots and git.

### 4. Verify

Start a new agent turn so OpenClaw reloads its skills, then:

```bash
qualia version        # CLI and SDK versions
qualia auth status    # the key is configured, and its scope; never prints the key
qualia credit --json  # the balance: proves the key and the connection
```

If the install says it completed but the agent doesn't mention the Qualia skill on the next turn, check that:

1. `~/.openclaw/workspace/skills/qualia-skill/SKILL.md` exists;
2. the skill isn't disabled under `skills.entries.qualia.enabled`;
3. `QUALIA_API_KEY` is set for the agent's environment, and `qualia` is on its `PATH`;
4. you started a fresh agent turn after installing.

### Claude Code and other agents

`SKILL.md` is a self-contained instruction set. Drop it into any agent that has shell access and the `qualia` CLI installed.

## What it costs

Uploading, preparation and the automatic checks are free. The VLM check spends credits from the account: the agent runs `qualia check estimate` first and asks you before starting it.

## Training

Training isn't available on plans yet. To request access, write to [support@qualiastudios.dev](mailto:support@qualiastudios.dev).

## Links

- [Qualia](https://qualiastudios.dev)
- [Qualia docs](https://docs.qualiastudios.dev)
- [OpenClaw](https://github.com/openclaw/openclaw)
- [ClawHub](https://clawhub.ai)

## License

MIT
