"""Assemble dependency-free local HTML from an immutable feeder topology snapshot."""
from pathlib import Path
import argparse

def build(root:Path,out:Path):
    template=(root/'template.html').read_text(encoding='utf-8')
    data=(root/'topology_snapshot.json').read_text(encoding='utf-8')
    engine=(root/'engine.js').read_text(encoding='utf-8')
    app=(root/'app.js').read_text(encoding='utf-8')
    # Avoid accidental closure of inline scripts from future DSS names.
    if any('</script' in s.lower() for s in (data,engine,app)):
        raise ValueError('Embedded content contains a closing script tag')
    doc=template.replace('/*DATA_INSERT*/','const P2_DATA='+data+';').replace('/*ENGINE_INSERT*/',engine).replace('/*APP_INSERT*/',app)
    if any(x in doc for x in ('/*DATA_INSERT*/','/*ENGINE_INSERT*/','/*APP_INSERT*/')):
        raise ValueError('Template replacement incomplete')
    # Write the canonical UTF-8 bytes directly. Windows text output would
    # translate LF to CRLF and break the pinned index.html byte parity.
    out.write_bytes(doc.encode('utf-8'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.root,a.out)
