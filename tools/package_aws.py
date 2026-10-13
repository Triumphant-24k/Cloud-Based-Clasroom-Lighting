from pathlib import Path
import json
from cfnlint.decode import decode
root=Path(__file__).resolve().parents[1]
raise SystemExit('Cloud vision uses tools.package_vision; do not deploy the old inline lighting-only package.')
template, errors=decode(str(root/'cloud/template.yaml'))
assert not errors, errors
handler=(root/'cloud/lambda_handler.py').read_text()
start=handler.index('try:\n    from .decision import decide')
end=handler.index('\nCONFIG=',start)
handler=handler[:start]+(root/'cloud/decision.py').read_text()+handler[end:]
handler=handler.replace("CONFIG=json.loads((Path(__file__).parent/'decision_config.json').read_text())",'CONFIG='+repr(json.loads((root/'cloud/decision_config.json').read_text())))
props=template['Resources']['DecisionFunction']['Properties']
props.pop('CodeUri')
props['InlineCode']=handler
props['Handler']='index.handler'
out=root/'cloud/deployment-template.json';out.write_text(json.dumps(template,indent=2))
print('Prepared cloud code directly from tested sources; template bytes:',out.stat().st_size)
