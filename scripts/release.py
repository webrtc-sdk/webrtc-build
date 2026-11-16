#!/usr/bin/env python3
"""Release helpers used by the release workflows.

    release.py check-version 150.7871.08
    release.py set-version 150.7871.08 --commit <sha> [--file VERSION]
    release.py get --key WEBRTC_COMMIT [--file VERSION]
    release.py notes --base <sha> --head <sha> --version 150.7871.08 [--out notes.md]

`notes` lists the webrtc commits between the previous release (--base) and
this one (--head) through the GitHub compare API. It reads GH_TOKEN (or
GITHUB_TOKEN) when set, and WEBRTC_REPO (owner/name, default
webrtc-sdk/webrtc).
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from typing import Dict, List

VERSION_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
DEFAULT_WEBRTC_REPO = 'webrtc-sdk/webrtc'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_version(version: str):
    m = VERSION_RE.match(version)
    if not m:
        raise SystemExit(f'invalid version {version!r}: expected <milestone>.<branch>.<patch>, '
                         'e.g. 150.7871.08')
    return m.groups()


def read_version_file(path: str) -> Dict[str, str]:
    result = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip()
    return result


def write_version_file(path: str, version: str, commit: str):
    milestone, branch, patch = parse_version(version)
    lines = [
        f'WEBRTC_BUILD_VERSION={version}',
        f'WEBRTC_VERSION={version}',
        f'WEBRTC_READABLE_VERSION=M{milestone}.{branch}@{{#{int(patch)}}}',
        f'WEBRTC_COMMIT={commit}',
    ]
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def github_get(path: str):
    req = urllib.request.Request(f'https://api.github.com/{path}')
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'webrtc-build-release')
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def compare_commits(repo: str, base: str, head: str) -> List[dict]:
    """Commits in head that are not in base, oldest first (up to 250)."""
    if base == head:
        return []
    data = github_get(f'repos/{repo}/compare/{base}...{head}')
    return data.get('commits', [])


def render_notes(repo: str, version: str, base: str, head: str, commits: List[dict]) -> str:
    url = f'https://github.com/{repo}'
    out = [
        f'## WebRTC {version}',
        '',
        f'Built from [{repo}@{head[:10]}]({url}/commit/{head}).',
        '',
    ]
    if base and base != head:
        out += [f'### Changes since previous release ([compare]({url}/compare/{base[:10]}...{head[:10]}))', '']
    if not commits:
        out.append('No new commits since the previous release.')
    for c in reversed(commits):  # newest first
        subject = c['commit']['message'].splitlines()[0]
        # "(#329)" refers to the webrtc repository, not this one.
        subject = re.sub(r'\(#(\d+)\)', rf'({repo}#\1)', subject)
        author = (c.get('author') or {}).get('login') or c['commit']['author']['name']
        out.append(f'- [`{c["sha"][:10]}`]({url}/commit/{c["sha"]}) {subject} ({author})')
    if len(commits) >= 250:
        out += ['', f'Only the first 250 commits are listed; see the compare link for all.']
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='op', required=True)

    p = sub.add_parser('check-version')
    p.add_argument('version')

    p = sub.add_parser('set-version')
    p.add_argument('version')
    p.add_argument('--commit', required=True)
    p.add_argument('--file', default=os.path.join(ROOT_DIR, 'VERSION'))

    p = sub.add_parser('get')
    p.add_argument('--key', required=True)
    p.add_argument('--file', default=os.path.join(ROOT_DIR, 'VERSION'))

    p = sub.add_parser('notes')
    p.add_argument('--base', required=True, help='webrtc commit of the previous release')
    p.add_argument('--head', required=True, help='webrtc commit of this release')
    p.add_argument('--version', required=True)
    p.add_argument('--out')

    args = parser.parse_args()
    if args.op == 'check-version':
        parse_version(args.version)
    elif args.op == 'set-version':
        if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
            raise SystemExit(f'--commit must be a full SHA, got {args.commit!r}')
        write_version_file(args.file, args.version, args.commit)
    elif args.op == 'get':
        print(read_version_file(args.file)[args.key])
    elif args.op == 'notes':
        repo = os.environ.get('WEBRTC_REPO') or DEFAULT_WEBRTC_REPO
        notes = render_notes(repo, args.version, args.base, args.head,
                             compare_commits(repo, args.base, args.head))
        if args.out:
            with open(args.out, 'w', newline='\n') as f:
                f.write(notes)
        else:
            sys.stdout.write(notes)


if __name__ == '__main__':
    main()
