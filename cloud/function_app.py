import json
import os
import azure.functions as func

app=func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route='lighting',methods=['POST'])
def lighting(req:func.HttpRequest)->func.HttpResponse:
    try:
        metadata=req.get_json()
        zones=['FRONT_LEFT','FRONT_RIGHT','MIDDLE_LEFT','MIDDLE_RIGHT','BACK_LEFT','BACK_RIGHT']
        occupied=metadata['occupiedZones'];ambient=float(metadata['ambientLight'])
        if set(occupied)!=set(zones) or any(type(v) is not bool for v in occupied.values()): raise ValueError('Invalid zones')
        bright=float(os.getenv('BRIGHT_THRESHOLD','700'));moderate=float(os.getenv('MODERATE_THRESHOLD','300'))
        level=int(os.getenv('BRIGHT_BRIGHTNESS','30')) if ambient>=bright else int(os.getenv('MODERATE_BRIGHTNESS','60')) if ambient>=moderate else int(os.getenv('DARK_BRIGHTNESS','100'))
        lights={f'LIGHT_{i+1}':level if occupied[z] else 0 for i,z in enumerate(zones)}
        return func.HttpResponse(json.dumps({'lights':lights}),mimetype='application/json')
    except (ValueError,KeyError,TypeError): return func.HttpResponse('Invalid occupancy metadata',status_code=400)
