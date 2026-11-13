"""Prepare pinned OFL-licensed TrueType report fonts; no private font files needed."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
root=Path(__file__).resolve().parents[1];spec=json.loads((root/'configs/report-fonts.json').read_text());out=root/'.cache/report-fonts';out.mkdir(parents=True,exist_ok=True)
variable=out/'NotoSansSC-variable.ttf'
if not variable.exists():
 with urlopen(spec['source_url'],timeout=60) as r:variable.write_bytes(r.read())
if hashlib.sha256(variable.read_bytes()).hexdigest()!=spec['variable_sha256']:raise SystemExit('Font source checksum mismatch')
with urlopen(f"https://raw.githubusercontent.com/google/fonts/{spec['revision']}/ofl/notosanssc/OFL.txt",timeout=30) as r:(out/'OFL.txt').write_bytes(r.read())
font=TTFont(variable)
if 'glyf' not in font:raise SystemExit('A TrueType glyf font is required')
for weight,name in [(400,'Regular'),(700,'Bold')]:
 instance=instantiateVariableFont(font,{'wght':weight},inplace=False,updateFontNames=True);instance.save(out/f'NotoSansSC-{name}.ttf')
print('Report fonts ready. Font software remains under SIL OFL 1.1.')
