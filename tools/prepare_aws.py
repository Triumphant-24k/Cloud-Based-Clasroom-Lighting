"""Run before sam build to synchronize local/cloud lighting settings."""
import json
from backend.config import ROOT, load_config

def prepare():
    config, zones, mapping = load_config()
    keys=('bright_threshold','moderate_threshold','bright_brightness','moderate_brightness','dark_brightness')
    output={'classroom_id':config['classroom_id'],'settings':{k:config[k] for k in keys},'mapping':mapping}
    (ROOT/'cloud/decision_config.json').write_text(json.dumps(output,indent=2)+'\n')
    return output

if __name__=='__main__': print('AWS configuration prepared for '+prepare()['classroom_id'])
