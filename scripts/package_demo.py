"""Build a portable source/demo archive from an explicit allowlist; never include raw data."""
import argparse
from hashlib import sha256
import json
import tomllib
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED


ROOT=Path(__file__).resolve().parents[1]
DIRECTORIES=('app','src','scripts','tests','research','data')
FILES=('streamlit_app.py','README.md','DEPLOYMENT.md','LICENSE','.python-version','pyproject.toml','requirements.txt','requirements-dev.txt','requirements.lock.txt',
       '.gitignore','.streamlit/config.toml','.github/workflows/tests.yml')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']
    parser.add_argument('--output',type=Path,default=ROOT/f'.local/winners-curse-lab-v{version}.zip')
    args=parser.parse_args()
    paths=[ROOT/name for name in FILES]
    for name in DIRECTORIES:
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store')
    paths=sorted(paths)
    if any(p.is_symlink() or not p.resolve().is_relative_to(ROOT) for p in paths):
        raise ValueError('Do not package symlinks or paths outside the project.')
    manifest={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(args.output,'w',ZIP_DEFLATED) as archive:
        for path in paths:archive.write(path,path.relative_to(ROOT))
        archive.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    print(f'Packaged {len(paths)} files: {args.output}')


if __name__=='__main__':main()
