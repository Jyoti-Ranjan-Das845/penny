"""Verify every file in this extracted release using only Python's standard library."""
from pathlib import Path
import hashlib,json,os
root=Path(__file__).resolve().parent
manifest=json.loads((root/'MANIFEST.json').read_text())
for name,entry in manifest['files'].items():
    p=root/name
    assert p.is_symlink()==(entry['kind']=='symlink'),f'File type mismatch: {name}; extract with a symlink-preserving tool such as macOS ditto'
    data=os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
    assert hashlib.sha256(data).hexdigest()==entry['sha256'],f'Hash mismatch: {name}'
print(f"Verified {len(manifest['files'])} release files.")
