"""Fast, independent structural checks for authored HyperFrames scene files."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


class SceneParser(HTMLParser):
    def __init__(self, scene):
        super().__init__(convert_charrefs=True)
        self.scene = scene
        self.stack = []
        self.ids = {}
        self.root_ids = set()
        self.hosts = []
        self.scripts = []
        self.script = None
        self.issues = []
        self.root_count = 0

    def issue(self, message):
        self.issues.append({'line': self.getpos()[0], 'message': message})

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        parent_root = any(item[1].get('id') == 'root' for item in self.stack)
        is_root = values.get('id') == 'root'
        if is_root:
            self.root_count += 1
        identifier = values.get('id')
        if identifier:
            if identifier in self.ids:
                self.issue('Duplicate element id: ' + identifier)
            self.ids[identifier] = values
            if parent_root or is_root:
                self.root_ids.add(identifier)
        if self.scene and tag not in ('template', 'style', 'script') and not parent_root and not is_root:
            self.issue(f'<{tag}> is outside the scene root. Keep every visible element inside <div id="root">.')
        if values.get('data-composition-src'):
            self.hosts.append(values)
        if tag == 'script':
            self.script = []
        if tag not in VOID:
            self.stack.append((tag, values))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.issue('Unexpected closing tag: </' + tag + '>')
        elif self.stack[-1][0] != tag:
            self.issue('Closing </' + tag + '> does not match open <' + self.stack[-1][0] + '>.')
            # Retain the stack to expose the originating malformed subtree.
        else:
            self.stack.pop()
        if tag == 'script' and self.script is not None:
            self.scripts.append(''.join(self.script))
            self.script = None

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def finish(self):
        if self.stack:
            self.issue('Unclosed tags: ' + ', '.join(tag for tag, _ in self.stack[-5:]))
        if self.root_count != 1:
            self.issue('Expected exactly one element with id="root".')
        for script in self.scripts:
            for match in re.finditer(r'\.(?:fromTo|from|to|set)\(\s*([\"\x27])(.+?)\1', script):
                for identifier in re.findall(r'#([A-Za-z_][\w-]*)', match.group(2)):
                    if identifier not in self.root_ids:
                        self.issue('Animation target #' + identifier + ' is missing from the scene root.')
        return self.issues


def validate(project):
    project = Path(project).resolve()
    pending = [(project / 'index.html', False)]
    seen = set()
    findings = []
    while pending:
        file, scene = pending.pop(0)
        file = file.resolve()
        if not file.is_relative_to(project) or file in seen:
            if not file.is_relative_to(project):
                findings.append({'file': str(file), 'message': 'Composition escapes the project folder.'})
            continue
        seen.add(file)
        if not file.is_file():
            findings.append({'file': str(file.relative_to(project)), 'message': 'Mounted composition file is missing.'})
            continue
        parser = SceneParser(scene)
        parser.feed(file.read_text(encoding='utf-8-sig'))
        findings.extend({'file': str(file.relative_to(project)), **item} for item in parser.finish())
        for host in parser.hosts:
            pending.append((project / host['data-composition-src'], True))
    return {'ok': not findings, 'findings': findings, 'files_checked': len(seen)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', nargs='?', default='.')
    args = parser.parse_args()
    result = validate(args.project)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
