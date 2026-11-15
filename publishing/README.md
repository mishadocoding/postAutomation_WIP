# Push a finished video to Instagram from this PC

## Scheduler-driven finished-file posts

An explicitly scheduled finished video runs through the existing background
worker in either schedule mode. Registering it copies the video and caption into
local state and makes no Meta requests:

```powershell
python .\automation.py schedule-file --video .\video.mp4 --caption-file .\caption.txt --at "2026-11-15T14:44:00+05:00"
python .\automation.py status
```

Use a future time. Keep the already-installed task running; no foreground
publisher is needed. The worker publishes on its first poll at/after the target,
inside the configured catch-up window. This path publishes a supplied finished
file, with no generation or visual-review loop. It does not release maintenance,
change the daily generation schedule, or reuse past failed generation slots.

Scheduled files stay out of the legacy daily FIFO. SHA-256 checks, publisher
state reconciliation and bounded attempts protect against repeat posting. The
worker records its user, Python executable, PID and target in `execution` on the
publisher job; `scheduled_files` in the queue database records execution and
completion. A pre-existing manual publication is reconciled without being
labelled a new worker publication. Completion/held notifications are recorded.

Separate task copies share a worker lock. Polls within the same configured
interval are coalesced; logs say `Duplicate poll in this interval` instead of
performing the workflow twice. This does not delete task registrations.

On November 15 the 14:44 scheduler-only test, item `174bade3fa32`, was claimed by
the background worker at 14:44:00 and publication was confirmed at 14:44:36
Tashkent: https://www.instagram.com/reel/DfwfMsjk7eF/. The publisher execution
record identifies Elyor, `pythonw.exe`, PID 3592 and `scheduled_file_worker`.
Its success notification is recorded. This proves scheduler-driven publication
of a supplied finished file; it does not prove unattended AI generation/review.
A different approved, unposted MacBook order/stock video is queued for 15:00
the same day, item `918ea739dc34`. The daily 18:00 target remains unchanged.

## Network diagnostics and recovery

Run this from the same signed-in Windows account used to install the task:

```powershell
python .\network_check.py
python .\push_reel.py --check-account
```

The diagnostic sends credential-free GET requests to the Graph and upload hosts,
records the actual Windows identity and Python executable, and saves its report
to ignored `.state/network/latest.json`. A received HTTP response, including an
error response, establishes HTTP reachability only; it does not prove account
permissions or upload success. The account check is separate and also read-only.
No generation, upload or publication is attempted by either command.

Windows error 10013 / errno 13 identifies operating-system access denial for that
process. DNS, TLS and timeout failures have different categories. A restriction
on the Codex sandbox account does not establish that the normal scheduled user
has the same restriction. The worker log now includes its username and Python
executable to make that distinction visible. Do not disable TLS verification or
change firewall rules based solely on a failed sandbox request.

Temporary transport failures on GET requests receive at most three attempts,
with one- and three-second delays. Access denial, certificate errors and HTTP
authentication errors are not retried this way. POST requests, including file
upload and publication, are never blindly retried by this transport layer:
the existing saved-state reconciliation remains responsible for their recovery.
The worker can resume an approved candidate after a network failure within its
scheduled publication window.

## Recovery validation

Scheduled generation and publication resumed after the November 15 test project
passed independent review on November 14. Its verified evidence is in
`.state/generation/test-17841473337457297/2026-11-15/recheck-1794670214948822900/`.
All nine review checks passed with no findings or uncertainties, and approval
hashes and current product source were verified before maintenance was lifted.
The next daily target is November 15 at 18:00 Tashkent, with preparation from
17:10. No recovery test was uploaded or published.

A one-off live sample is also scheduled for November 14 at 21:30 Tashkent.
It uses a separate `2026-11-14_2130` run folder and the normal generation,
review/repair, publishing and notification gates. Preparation is eligible
immediately; publication waits until 21:30. This extra slot does not recur.

Set `maintenance: true` in `schedule.json` to hold scheduled work. The task
continues polling, but skips live work while this flag is set. A no-publish test
can still exercise the complete generation,
technical checks, rendering, duplicate screening and independent visual review:

```powershell
python .\generation.py test --date 2026-11-15
python .\automation.py status
```

Run the test in your normal signed-in Windows terminal. A successful result
says `Generation test passed all gates`; `run.json` has phase `reviewed`.
The test does not upload or publish and does not release the maintenance hold.
The status command includes the latest test and its current stage.

After a deliberate manual source repair to an existing test, recheck it with:

```powershell
python .\generation.py recheck --date 2026-11-15
```

This does not run the author or reset the unattended three-attempt limit. It
creates separate evidence, reruns real browser checks, renders and decodes the
current project, checks source freshness and novelty, and runs independent visual
review. It never uploads/publishes or changes maintenance. Rejected reviews
continue to hold the test. Older evidence and failed attempts are preserved.

The failed November 14 samples exposed malformed scene markup and an author
incorrectly blocking on missing prior-video evidence. The runner now performs a
local scene-structure preflight, owns duplicate screening, supplies those results
to the reviewer, and gives repair attempts concise findings with browser crops.
Unchanged product snapshots are reused; an interrupted process can resume its
attempt. Timed-out command output is retained for diagnosis. These fixes have
regression coverage, and the real no-publish recheck described above has passed.
The expired sample slots are not replayed.

## Current sampleERP automation and today's sample posts

The product source is now `C:\Users\hadzhee2K\Documents\sampleERP`, configured in
`project_source.json`. A separate manually written brief is no longer required:
the worker snapshots the saved working tree and writes a new factual demo brief.
This includes uncommitted changes. It does not pull a remote Git repository.
The source is checked before generation, after review, during preparation checks,
and immediately before `media_publish`. If it changed, the approved old version
is held and a new version is generated within the three-attempt limit.

The one-off sample targets are **November 14, 2026 at 18:30 and 19:00 Tashkent**.
Today's original 18:00 slot is explicitly excluded. The 18:30 slot reuses the
original day's run folder so work and publishing history are preserved. Restart
any already-running worker after rescheduling; future workers also reload the
schedule immediately before uploading/publishing to reject cancelled slots.
The ongoing daily target remains **18:00**. The 19:00 sample does not recur on
other dates. The task checks every two minutes, prepares videos up to fifty
minutes early, and can upload/process a reviewed video ahead of its target.
Publication itself is never intentionally early. Timing depends on successful
generation/review, the polling interval and Meta's response; a missed quality
gate holds the post instead of forcing a bad or outdated upload. Posts over an
hour late are held for attention.

Start preparation now and install/update the scheduled worker from your own
signed-in PowerShell session:

```powershell
python .\install_task.py --install --update --start
```

For a foreground live run, useful for seeing the first generation logs:

```powershell
python .\automation.py run --live --log
```

Both commands can generate, upload and publish when a target is due. The first
starts the registered windowless task; the second stays attached until the
current work completes. Normal single-instance locks prevent concurrent workers.

Old video file hashes and 16 normalized decoded-frame difference hashes are
compared with each candidate. Exact and near-visual duplicates are rejected,
including re-encodes of the already-posted SampleERP Reel. The author also gets
recent storyboard history and a different subject/style/edition instruction.
These checks substantially reduce repeats but cannot mathematically guarantee
semantic uniqueness under every possible video edit. A repeated topic is allowed;
a failed novelty check requires a different hook/composition/shot sequence.

Success and held-post events show a Windows tray notification. Clicking a success
notification opens the Instagram link when available. Windows notification/Focus
Assist settings may hide banners; the events are also saved in
`.state/notifications/events.jsonl`. These notifications are local to this Windows
user, not messages sent to other people. Test locally with:

```powershell
python .\notifications.py --test
python .\automation.py status
```

Run folders are distinct for each slot: the ordinary 18:00 run uses `YYYY-MM-DD`,
and the additional 19:00 run uses `YYYY-MM-DD_1900`. Their source manifests retain
the exact product file hashes used to produce each film. Review evidence and
novelty history are kept locally; original sampleERP source files are never edited.

## Daily generation, repair, review and publishing

The selected schedule mode is **generate**. Preparation starts before the target
publication time as described above. Failed checks, missing tools, or uncertain
review mean no post. The older finished-video queue is inactive in this mode.
The following manual-brief instructions apply if automatic product briefs are
disabled by setting `project_source.json`'s `enabled` field to false.

1. Read `briefs/brief-template.txt` and put the approved brief in
   `briefs/YYYY-MM-DD.md`, using the intended Tashkent posting date.
2. Put optional approved product screenshots, images, music, and fonts in
   `briefs/assets/YYYY-MM-DD/`. These are copied into that day's project.
3. Check the installed tools and CLI sign-in from your own PowerShell:

   ```powershell
   python .\generation.py doctor
   ```

   If Codex is not signed in, run `codex login` in that same Windows account.
   No OpenAI API key is required when working saved CLI authentication is used.
   Codex usage is subject to your account's available allowance; installing
   HyperFrames does not provide unlimited AI generation.

4. Test a real brief with generation/review but **no publishing**:

   ```powershell
   python .\generation.py test --date 2026-11-16
   ```

   Replace the example date with the matching brief's date. This invokes Codex,
   consumes AI usage, and renders locally. It never uploads to Instagram. Test
   artifacts live separately from live runs and cannot accidentally become a
   scheduled live approval.

5. Install or update the daily Windows task after checking the configuration:

   ```powershell
   python .\install_task.py --install --update
   ```

   `--update` only replaces an existing task when its principal and worker path
   match this publisher/current user; a backup of its XML is saved first. The
   generation task has a 105-minute execution limit. The previous queue-only task
   had a 15-minute limit, so update it even if it was already installed.

At 18:00 the worker freezes the day's brief/assets, creates an isolated editable
HyperFrames project with Codex, and applies this loop:

```text
Generate -> strict browser/layout/contrast/motion/audio checks
         -> render and decode MP4
         -> sample final MP4 at 4 fps + exact first frame
         -> inspect source beat/seam/phone sheets with a separate Codex review
         -> repair failures and repeat checks/render/review
         -> upload/publish only after all gates pass
```

There are **three total generation attempts**, with a 90-minute command budget.
The final MP4 must match the source timeline duration and be 1080x1920 at 30 fps,
up to 45 seconds. A real motion spec with assertions and non-skipped browser
checks are required. The visual review must confirm text legibility, object
identity, item matching, continuity, contact/motion, framing/layers, and factual
consistency with the brief/caption. A P0/P1 finding, uncertainty, missing review
image, or mismatched video hash prevents publication. Technical and visual
checks cannot guarantee that a video has zero mistakes: 4 fps sampling can miss
very brief defects, model review can miss errors, and the system does not listen
to the audio. Audio is technically decoded; essential unverified audio judgments
must hold the post. The first real brief still needs an end-to-end generation test.

Approvals bind the exact video, source, caption, brief, technical report, and
review/image evidence hashes. Changes invalidate approval. A failed upload reuses
the approved video on retry rather than generating a different one. Existing
publisher protections handle uncertain publish responses and duplicate uploads.
Missing or rejected generation never falls back to posting an unreviewed queued
video. Automatic sampleERP briefs are based only on the current captured app.

Configuration is in `generation.json` and `schedule.json`. The Node executable
is pinned to the installed Node 26 path because the default Nodist Node 20 is
too old. HyperFrames 0.9.39 is reused from the existing npm cache. The generator
uses Codex's default configured model and saved login. Agent calls have bounded
timeouts, run with approvals set to never, and retain their normal read-only or
workspace-write sandbox; no dangerous permission bypass is used. Blocked tool
access fails the attempt. The Instagram token variables are stripped from AI/
render subprocess environments. Keep secrets out of briefs/assets.

Live run projects/reports/videos are saved under
`.state/generation/INSTAGRAM_ID/YYYY-MM-DD/`. Each attempt has its own evidence;
`run.json` records `awaiting_brief`, `generating`, `approved`, `needs_attention`,
or `published`. No old output is automatically removed. Inspect the failure
reports before resetting any failed run; `needs_attention` is not bypassed by
the scheduler. Repeated task invocations cannot post the same day's run twice.

## Optional finished-video queue: mode=queue

The queue publishes **one finished video per day at 18:00 (UTC+05:00)**, oldest
first. No video is generated. Add each video and caption once; the queue copies
the video and stores the caption so later source edits do not change the post.
Already-published and duplicate files are rejected during enqueue.

```powershell
python .\automation.py add --video "C:\path\to\next-video.mp4" --caption-file "C:\path\to\caption.txt"
python .\automation.py status
```

The first SampleERP Reel has already been published, so use a different video.
Queueing is authorization to publish that video/caption at the next available
daily slot. There are no recurring or reposting entries.

Install the background task once from this folder:

```powershell
python .\install_task.py --install
```

Without `--install`, that command only previews the task. The installer refuses
to replace an existing task of the same name. Its name is
`PostAutomation-Instagram`. It runs windowlessly as your signed-in Windows user,
with limited privileges and no saved password. You can lock Windows or close
PowerShell. You must remain signed in; shutdown/sign-out prevents execution.
Wake timers may wake a sleeping PC where supported, but cannot power it on.
The script checks the Windows timezone before registering an 18:00 trigger.
Run installation in your own PowerShell session; the installer refuses the
agent's sandbox Windows identity. It does not change PowerShell execution policy.

The task requests a run after a missed start. The worker only catches up during
18:00–18:59 Tashkent time; later missed slots are skipped. An empty queue consumes
that day's slot without posting. Items added afterward wait for the following
day. Only one item may be assigned to a daily slot, even after a crash/restart.
There are at most three attempts for that item, with five-minute retry intervals.
Confirmed zero-byte upload failures are recovered on the existing container on
the next attempt. Uncertain create/publish operations stop for inspection.

The queue is held in `.state/automation/queue.sqlite3`, immutable video copies
in `.state/automation/assets/`, and daily logs in `.state/automation/logs/`.
Publisher duplicate records remain in `.state/posts.sqlite3`. Keep these when
moving to the company server. Video copies and logs are not automatically removed.
Expired/revoked tokens stop publication; long-lived token setup is still needed
for ongoing unattended use. The worker cannot renew credentials by itself.

```powershell
# Offline preview only; never posts:
python .\automation.py run
# Queue/history, attempt counts, and errors:
python .\automation.py status
# Read today's log:
Get-Content .\.state\automation\logs\2026-11-14.log
# Pause or resume automatic posting:
Disable-ScheduledTask -TaskName PostAutomation-Instagram
Enable-ScheduledTask -TaskName PostAutomation-Instagram
```

`automation.py run --live` is the actual worker; it can publish inside the daily
window and should normally be invoked by Task Scheduler. `--log` saves its output.
After investigating a `needs_attention` item, `automation.py retry ITEM_ID` returns
it to the queue for a future daily slot. It refuses to bypass uncertain or already
published state. No deletion of duplicate records is needed for recovery.

Schedule settings live in `schedule.json`. Reinstall/update the Windows trigger
if changing `daily_time`; changing the JSON alone does not reschedule Windows.

This script publishes an existing MP4/MOV as an Instagram Reel. It does not generate
or edit videos. Python 3.11+ and FFmpeg's `ffprobe` on PATH are required. There are
no pip packages to install. Use either Python directly or the PowerShell wrapper.

## Try it without an account

Open PowerShell in this folder:

```powershell
python .\push_reel.py --video ..\instagram\renders\circuit-market-instagram.mp4 --caption-file .\caption.example.txt
```

This is an offline dry run. It checks the media and caption and prints a summary.
It does not upload, connect to Meta, or publish anything. These are basic technical
checks; they do not certify every Meta encoding rule or the creative quality.

## Set up the new test account

1. Create the Instagram test account normally and switch it to a professional
   account (Business is a suitable choice). Create a Facebook Page and connect it.
2. Create a company-owned Meta developer app at https://developers.facebook.com/.
   Use **Facebook Login for Business** with Instagram publishing. This particular
   script does not use Instagram Login tokens.
3. For a development test, add the relevant Facebook/Instagram users as app
   roles/testers and accept any invitations. Publishing to accounts outside the
   app's permitted development roles may require App Review/Advanced Access.
4. Obtain an access token for the authorized user/Page that can publish to the
   connected Instagram account. The publishing route needs `instagram_basic`,
   `instagram_content_publish`, and `pages_read_engagement`. Account discovery
   typically also uses `pages_show_list`; some business ownership arrangements
   need additional permissions. Use the app's current setup instructions.
5. Find the numeric Instagram account ID from the Page's
   `instagram_business_account` field using Meta's Graph API Explorer. This is
   not the Page ID or the account's @username.
6. Copy `.env.example` to `.env` and enter the API version from your app dashboard,
   Instagram account ID, and token. Never paste the token into chat or commit it.
   Environment variables override `.env` values. No app secret or Instagram
   password is required by this script.

```powershell
Copy-Item .env.example .env
notepad .env
```

After saving `.env`, check the account without uploading or publishing:

```powershell
python .\push_reel.py --check-account
```

This prints the account username and the publishing allowance returned by Meta.
It uses read-only requests, does not print credentials, and does not prove that
a particular video will pass Meta's processing or publishing checks.

Tokens can expire or be revoked. This first version reports authentication failures;
it does not automate OAuth login, token renewal, account creation, or App Review.
Keep `.env` in a private company-controlled folder, especially on shared PCs.

## Publish deliberately

Review the video and replace `caption.example.txt` with your intended caption.
Pass `--publish` only for a post you intend to make public:

```powershell
python .\push_reel.py --video ..\instagram\renders\circuit-market-instagram.mp4 --caption-file .\caption.example.txt --publish
```

Equivalent wrapper, if local PowerShell policy permits running scripts:

```powershell
.\push-reel.ps1 -Video ..\instagram\renders\circuit-market-instagram.mp4 -CaptionFile .\caption.example.txt -Publish
```

The script reads the target account, creates a resumable-upload container, sends
the local file directly to Meta, polls processing, and publishes. No public video
hosting is necessary. The default also shares to the feed; `--reels-only` changes
that. It prints the post link when available. Audio must already be in the video;
this script does not add Instagram library music. Preserve required attribution
in the caption when using licensed music.

## Local scheduling

```powershell
python .\push_reel.py --video ..\instagram\renders\circuit-market-instagram.mp4 --caption-file .\caption.example.txt --publish --at "2026-11-14T18:00:00+05:00"
```

Replace the example date. The command waits in the foreground, then starts the
upload at the chosen time. Processing means the public post appears later.
Your PC must be awake, online, and running the script. A closed shell stops it.
The time is saved before waiting; rerunning the same command resumes that job.
If the time has passed, it runs immediately. Changing `--at` does not reschedule
an existing job. This is a single-job script, not a background queue daemon.

Alternatively, use **Windows Task Scheduler → Create Basic Task** for a one-time
trigger. Select **Start a program**, use the full path to your Python executable,
and supply full paths to the script, MP4, and caption in the arguments. Include
`--publish` and omit `--at`. Set **Start in** to this publishing folder. Configure
**Wake the computer to run this task** if supported. An overdue task runs late
if configured to start after a missed trigger; it cannot post from a powered-off PC.
No Windows task has been registered by this project.

## Saved state and failures

For a failed run, use its printed Job ID to inspect the saved phase and Meta's
current processing/upload status without repeating any upload or publish:

```powershell
python .\push_reel.py --inspect-job YOUR_64_CHARACTER_JOB_ID
```

This uses read-only API calls and opens the saved database in read-only mode.
Upload errors now display sanitized `debug_info` messages as well as Graph API
errors; tokens and URLs are redacted. Do not delete state to get past a failure.

If the saved phase is `uploading` and Meta reports `IN_PROGRESS` with
`uploading_phase.status=error` and zero bytes transferred, retry just the file
upload on that same container:

```powershell
python .\push_reel.py --retry-upload YOUR_64_CHARACTER_JOB_ID
```

This verifies that the local video is unchanged and rechecks Meta's status first.
It neither creates another container nor calls `media_publish`. On acceptance it
marks the saved job as processing. Run `--inspect-job` next; once processing is
finished, the original `--publish` command resumes the existing job. Partial,
expired, terminal-error, or uncertain uploads are not overwritten by this command.

`.state/posts.sqlite3` records each account + video-content hash and its phase.
Keep this directory when moving the publisher to a server. It contains captions
and local paths, but no access token. Back it up with the publisher.

- Repeating a completed job skips publishing. Changing the caption or filename
  does not allow the same file bytes to be posted again to that account.
- Processing timeouts can be resumed with the same command and saved container.
- Lost publish responses are reconciled by checking the container status. The
  script never blindly repeats `media_publish` after an uncertain response.
- Interrupted create/upload operations stop for inspection. Confirmed zero-byte
  failures can use `--retry-upload`; partial-offset recovery and automatic retries
  are not implemented in this version.
- ERROR/EXPIRED containers require investigation before a replacement job.
- A process lock allows one publisher at a time; do not start parallel waiting
  commands. The lock is released automatically on exit.
- Do not delete the database to clear an error: doing so removes duplicate
  protection. A modified/re-encoded video has a new hash, so protection is not
  semantic duplicate detection.

## Offline verification

```powershell
python -m unittest -v test_push_reel.py test_automation.py test_generation.py test_recurring.py
```

Tests simulate success, rejected media, processing timeout, interrupted uploads,
lost publish responses, duplicate attempts, and an unavailable permalink. They
do not contact Instagram. Live API permissions and upload eligibility must still
be verified with the new account.

## API references

- [Meta's Reels publishing sample, including local resumable upload](https://github.com/fbsamples/reels_publishing_apis/tree/main/insta_reels_publishing_api_sample)
- [Meta's maintained Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)

The framework's `hyperframes publish` command shares a HyperFrames project; this
publisher's `--publish` sends a Reel to Instagram. They are separate operations.
