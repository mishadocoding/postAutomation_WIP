# SampleERP video and Instagram automation

Work in progress: create product demo Reels from the current SampleERP working
tree using Codex and HyperFrames, validate and repair them, then publish through
Meta's Instagram API. Windows Task Scheduler runs the local worker.

## Contents

- `publishing/`: generation, checks, visual review, repair, duplicate screening,
  Instagram publisher, scheduling, notifications and Python regression tests.
- `instagram/`: original editable vertical video, source captures, local media
  assets and sample renders.
- `instagram-v2/`: alternative video work and art direction.
- `STORYLINES.md`: initial creative directions.

Start with [the publishing setup guide](publishing/README.md). The worker needs
Python, Node.js 22+, FFmpeg/ffprobe, the pinned HyperFrames CLI and authenticated
Codex CLI with available usage. It also needs a professional Instagram account
linked to a Facebook Page and authorized Meta app credentials.

SampleERP itself is a separate application, not bundled in this repository.
Set `publishing/project_source.json` to its saved local working tree. Also adjust
the Node executable in `publishing/generation.json` for the deployment machine.
The committed configuration reflects the initial Windows installation.

Copy `publishing/.env.example` to `publishing/.env` and configure credentials
locally. Credentials, private execution logs, run databases and browser profiles
are ignored by Git. Keep the existing local `.state` folder when updating the
worker; it contains publication history used to prevent duplicate posts. A fresh
clone does not restore those operational records or install a scheduled task.

## Validate without posting

From `publishing/`:

```powershell
python -m unittest test_push_reel test_automation test_generation test_recurring test_structure test_network test_scheduled_posts
python .\generation.py doctor
python .\network_check.py
python .\push_reel.py --check-account
python .\automation.py run
```

The last command previews eligible slots without generating or publishing.
The complete no-publish generation test is documented in the publishing guide.

## Live operation

Review `publishing/schedule.json` before installing or starting the worker. It
contains the daily Tashkent target and dated one-off test slots. Set
`maintenance` to `true` to hold scheduled work while configuring a new machine.
Explicit live commands can generate, upload and publish once configured; leave
the PC awake and the configured Windows user signed in during scheduled work.

Candidates must pass structural and browser checks, render/decode validation,
source-freshness and duplicate screening, and independent visual review. Important
failures hold publication. These checks reduce defects but cannot guarantee that
every generated video is flawless. This is still a work-in-progress deployment.
