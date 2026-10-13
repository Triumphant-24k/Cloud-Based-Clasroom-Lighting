"""Build an ARM64 Lambda ZIP from downloaded Linux wheels; no Docker needed."""
import argparse
import json
import zipfile
from pathlib import Path
from cfnlint.decode import decode

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wheels',type=Path,required=True)
    parser.add_argument('--bucket',required=True)
    parser.add_argument('--key',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    wheels=list(args.wheels.glob('*.whl'))
    assert len(wheels)==3, 'Expected numpy, headless OpenCV and Pillow Linux wheels'
    size=0
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
        for wheel in wheels:
            assert 'aarch64' in wheel.name
            with zipfile.ZipFile(wheel) as source:
                for item in source.infolist():
                    if item.is_dir(): continue
                    data=source.read(item)
                    info=zipfile.ZipInfo(item.filename)
                    info.external_attr=0o100644<<16
                    info.compress_type=zipfile.ZIP_DEFLATED
                    archive.writestr(info,data);size+=len(data)
        paths=['cloud/__init__.py','cloud/vision.py','cloud/vision_handler.py','cloud/lambda_handler.py',
               'cloud/decision.py','cloud/decision_config.json','cloud/classroom_zones.json','cloud/yolov8n.onnx',
               'backend/__init__.py','backend/cv/__init__.py','backend/cv/zone_mapper.py']
        for name in paths:
            data=(ROOT/name).read_bytes()
            info=zipfile.ZipInfo(name);info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data);size+=len(data)
    assert size<250*1024*1024, 'Lambda ZIP exceeds uncompressed limit'
    template,errors=decode(str(ROOT/'cloud/template.yaml'));assert not errors
    props=template['Resources']['DecisionFunction']['Properties']
    props.update(CodeUri={'Bucket':args.bucket,'Key':args.key},Handler='cloud.vision_handler.handler',MemorySize=2048,Timeout=60)
    template['Resources']['DecisionFunction']['Metadata']={'com.aws.cloudformation.Context':{
        'why':'On-demand CPU vision, floor homography and lighting; no warm endpoint',
        'must':['IAM-authenticated URL','Images not persisted','ARM64 Linux dependencies','Bound request rate and concurrency']}}
    (ROOT/'cloud/vision-deployment-template.json').write_text(json.dumps(template,indent=2),encoding='utf-8')
    print(f'Lambda package: {size/1024/1024:.1f} MiB uncompressed, {args.output.stat().st_size/1024/1024:.1f} MiB compressed')

if __name__=='__main__': main()
