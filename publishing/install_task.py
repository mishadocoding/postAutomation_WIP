"""Register the daily queue task under the Windows user running this command."""
import argparse
import csv
from datetime import datetime, timedelta
import io
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import automation as a

NAME = 'PostAutomation-Instagram'
NS = 'http://schemas.microsoft.com/windows/2004/02/mit/task'
ET.register_namespace('', NS)


def task_xml(root, pythonw, sid, options, day):
    def node(parent, name, text=None, **attrs):
        element = ET.SubElement(parent, '{' + NS + '}' + name, attrs)
        if text is not None:
            element.text = str(text)
        return element
    task = ET.Element('{' + NS + '}Task', {'version': '1.2'})
    registration = node(task, 'RegistrationInfo')
    node(registration, 'Description', 'Start daily Instagram generation/check/repair/publish workflow at 18:00 Tashkent.'
         if options.get('mode') == 'generate' else 'Publish one queued Instagram Reel daily at 18:00 Tashkent.')
    triggers = node(task, 'Triggers')
    daily = node(triggers, 'CalendarTrigger')
    polling = options.get('mode') == 'generate' and options.get('poll_minutes')
    if polling:
        repetition = node(daily, 'Repetition')
        node(repetition, 'Interval', f"PT{options['poll_minutes']}M")
        node(repetition, 'Duration', 'P1D')
        node(repetition, 'StopAtDurationEnd', 'false')
    trigger_time = '00:00' if polling else options['daily_time']
    node(daily, 'StartBoundary', f"{day.isoformat()}T{trigger_time}:00+05:00")
    node(daily, 'Enabled', 'true')
    node(node(daily, 'ScheduleByDay'), 'DaysInterval', '1')
    principal = node(node(task, 'Principals'), 'Principal', id='Author')
    node(principal, 'UserId', sid)
    node(principal, 'LogonType', 'InteractiveToken')
    node(principal, 'RunLevel', 'LeastPrivilege')
    settings = node(task, 'Settings')
    for key, value in (
        ('MultipleInstancesPolicy', 'IgnoreNew'),
        ('DisallowStartIfOnBatteries', 'false'), ('StopIfGoingOnBatteries', 'false'),
        ('AllowHardTerminate', 'true'), ('StartWhenAvailable', 'true'),
        ('RunOnlyIfNetworkAvailable', 'false'), ('AllowStartOnDemand', 'true'),
        ('Enabled', 'true'), ('Hidden', 'false'), ('RunOnlyIfIdle', 'false'),
        ('WakeToRun', 'true'), ('ExecutionTimeLimit', 'PT105M' if options.get('mode') == 'generate' else 'PT15M'), ('Priority', '7')):
        node(settings, key, value)
    restart = node(settings, 'RestartOnFailure')
    node(restart, 'Interval', f"PT{options['retry_minutes']}M")
    node(restart, 'Count', options['max_attempts'] - 1)
    action = node(node(task, 'Actions', Context='Author'), 'Exec')
    node(action, 'Command', str(pythonw))
    node(action, 'Arguments', f'"{root / "automation.py"}" run --live --log')
    node(action, 'WorkingDirectory', str(root))
    return ET.ElementTree(task)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Register the task; otherwise preview only')
    parser.add_argument('--update', action='store_true', help='Update this publisher task if it already exists')
    parser.add_argument('--start', action='store_true', help='Start the worker after successful installation')
    args = parser.parse_args(argv)
    if args.update and not args.install:
        raise a.p.PushError('--update requires --install.')
    if args.start and not args.install:
        raise a.p.PushError('--start requires --install.')
    if sys.platform != 'win32':
        raise a.p.PushError('Run this installer on Windows under your normal signed-in user.')
    options = a.settings()
    if datetime.now().astimezone().utcoffset() != timedelta(hours=5):
        raise a.p.PushError('Windows timezone must be Tashkent (UTC+05:00) for this installer.')
    result = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise a.p.PushError('Could not identify the Windows task user.')
    username, sid = next(csv.reader(io.StringIO(result.stdout.strip())))
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file():
        raise a.p.PushError('pythonw.exe was not found alongside this Python interpreter.')
    print('Task:', NAME)
    print('User:', username)
    print('Daily time:', options['daily_time'], 'Tashkent (+05:00)')
    print('Workflow:', options.get('mode', 'queue'))
    if options.get('sample_slots'):
        print('Additional sample targets:', ', '.join(options['sample_slots']))
    if options.get('poll_minutes'):
        print('Worker check interval:', options['poll_minutes'], 'minutes; prepares up to', options.get('prepare_minutes', 0), 'minutes early')
    print('Program:', pythonw)
    print('Worker:', a.ROOT / 'automation.py')
    if not args.install:
        print('Preview only. Use --install from your own PowerShell window to register.')
        return 0
    if 'codexsandbox' in username.lower():
        raise a.p.PushError('Run installation from your own PowerShell window, not the agent sandbox account.')
    path = a.DATA / 'daily-task.xml'
    path.parent.mkdir(parents=True, exist_ok=True)
    task_xml(a.ROOT, pythonw, sid, options, datetime.now(a.TZ).date()).write(
        path, encoding='utf-16', xml_declaration=True)
    flags = []
    if args.update:
        existing = subprocess.run(['schtasks', '/Query', '/TN', NAME, '/XML'],
                                  capture_output=True, text=True, timeout=15)
        if existing.returncode == 0:
            document = ET.fromstring(existing.stdout.lstrip('\ufeff'))
            namespaces = {'t': NS}
            old_user = document.find('.//t:UserId', namespaces)
            old_args = document.find('.//t:Arguments', namespaces)
            if (old_user is None or old_user.text != sid or old_args is None
                    or str(a.ROOT / 'automation.py').lower() not in (old_args.text or '').lower()):
                raise a.p.PushError('Existing task does not match this publisher/current user; update refused.')
            (a.DATA / 'previous-daily-task.xml').write_text(existing.stdout, encoding='utf-16')
            flags = ['/F']
    result = subprocess.run(['schtasks', '/Create', '/TN', NAME, '/XML', str(path)] + flags,
                            capture_output=True, text=True, timeout=30)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise a.p.PushError('Task registration failed. Existing task settings were not overwritten.')
    print('Installed. You may close PowerShell; remain signed in and keep the PC available at posting time.')
    if args.start:
        started = subprocess.run(['schtasks', '/Run', '/TN', NAME], capture_output=True, text=True, timeout=15)
        print(started.stdout.strip())
        if started.returncode:
            raise a.p.PushError('Task was installed but could not be started; inspect it in Task Scheduler.')
    subprocess.run(['schtasks', '/Query', '/TN', NAME, '/FO', 'LIST'], check=False, timeout=15)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (a.p.PushError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('ERROR:', str(exc) if isinstance(exc, a.p.PushError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
