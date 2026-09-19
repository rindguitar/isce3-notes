#!/usr/bin/env python3
"""貼り付け用ファイルを作り直す。

`issue-reference-terrain-height.md` から足場（HTML コメント・`# Title` / `# Body`）を
外して `upstream-issue-paste-ready.md` を生成する。
編集は必ず元ファイル側で行い、こちらは作り直すこと。

    python3 drafts/regen-paste-ready.py
"""
import pathlib
import re

HERE = pathlib.Path(__file__).parent
src = (HERE / 'issue-reference-terrain-height.md').read_text()

# 1. 本文とタイトルを取り出す
body = src.split('# Body\n', 1)[1].lstrip('\n')
title = re.search(r'# Title\n\n(.+?)\n', src).group(1).strip()

# 2. そのまま貼れる形に組み直す
out = (
    '<!-- 🔴 これは「そのまま貼る」ための版。編集は drafts/issue-reference-terrain-height.md\n'
    '     側で行い、このファイルは `python3 drafts/regen-paste-ready.py` で作り直すこと。 -->\n\n'
    '## Title（issue のタイトル欄に入れる）\n\n'
    f'{title}\n\n'
    '---\n\n'
    '## Body（issue の本文欄に入れる。ここから下をそのまま貼る）\n\n'
    f'{body}'
)
(HERE / 'upstream-issue-paste-ready.md').write_text(out)
print(f'生成: upstream-issue-paste-ready.md（{len(out.splitlines())} 行）')
print(f'  タイトル: {title}')
