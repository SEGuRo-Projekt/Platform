import json
import argparse
import logging
import environ
from nicegui import ui, app
from datetime import datetime, timedelta
from seguro.common import broker, config
from functools import partial

env = environ.Env()
PORT = env.int("HB_MON_PORT", 9099)                 # port to be exposed for web-ui
HB_INTERVAL = env.int("HB_INTERVAL", 10)            # seconds 
CRITICAL_PCT = env.int("CRITICAL_RESOURCE_PCT", 95) # critical threshold to be flagged
WARNING_PCT = env.int("WARNING_RESOURCE_PCT", 75)   # critical threshold to be flagged

devices = []                        # list of dicts to store the dev hb info
device_table = None                 # global table 
state_colours = {'OK':      '🟢',   # map states to colors
                 'Warning': '🟠', 
                 'Critical':'🔴'} 

def update_device_states():
    if device_table:
        time_now = datetime.now()
        for d in devices:
            last_ping = datetime.strptime(d['last_ping'],"%H:%M:%S, %d/%m/%Y")
            time_diff = (time_now - last_ping).total_seconds()
            if time_diff > HB_INTERVAL:
                d['ping_status'] = 'offline'            
                if d['remark']:
                    if 'Offline' not in d['remark']:
                        d['remark'] = 'Offline and Warnings' if d['state'] == 'Warning' else d['remark'] +', Offline' 
                else:
                    d['remark'] = 'Offline'

                d['state'] = 'Critical'        
                d['state_colour'] = state_colours['Critical']
        
        device_table.rows = devices
        device_table.update()
        show_summary_card.refresh()

#global timer to trigger the state update fn
app.timer(HB_INTERVAL, update_device_states, immediate=False)

def state_calculator(curr_vals: dict):    
    # logic to calculate the maximum severity and 
    # add remarks to be displayed for each device on the web-ui
    level = 0
    state = 'OK'
    remarks = ""    
    for key, val in curr_vals.items():
        #logic to find the highest severity to be displayed 
        if val >= CRITICAL_PCT:
            if level == 2:
                remarks += ", "+key
            else:
                remarks = key
            level = 2
            state = 'Critical'
        elif val >= WARNING_PCT and level >= 0:
            if level == 1:
                remarks += ", "+key
            else:
                remarks = key
            level = 1
            state = 'Warning'
        
    return state, remarks

def new_device_hb(logger: logging.Logger, b: broker.Client, msg: broker.Message):
    #new heartbeat triggers the callback fn to update the device list & nicegui table     
    device_cur_vals = {"Memory Usage":0, "Disk Usage":0, "CPU Temperature":0}
    try:
        new_hb_device = {'mem_pct': None, 'cpu_thermal': None}                       
        data = json.loads(msg.payload)

        if "memory" in data:
            new_hb_device["mem_pct"] = data["memory"]["percent"]
            new_hb_device["mem_available"] = data["memory"]["available"]
            device_cur_vals['Memory Usage'] = new_hb_device["mem_pct"]
        if "cpu" in data:
            new_hb_device["cpu_freq"] = data["cpu"]["frequency"]["current"]
        if "sensors" in data:
            if "cpu_thermal" in data["sensors"]["temp"]:
                new_hb_device["cpu_thermal"] = data["sensors"]["temp"]["cpu_thermal"][0]
                #scaling the current temp to pct so as to apply the same logic in state_calculator()
                scaled_temp_pct = 100*new_hb_device["cpu_thermal"]["current"]/(new_hb_device["cpu_thermal"]["critical"]*1.05)
                device_cur_vals['CPU Temperature'] = scaled_temp_pct                
        if "disks" in data and data["disks"] != []:
            for partitions in data["disks"]:
                if partitions["mountpoint"] == "/":
                    new_hb_device["disk_pct"] = partitions["usage"]["percent"]
                    device_cur_vals['Disk Usage'] = new_hb_device['disk_pct']
        if "uptime" in data:
            sec = int(data["uptime"]["system"])%60
            minutes = int(data["uptime"]["system"]/60)%60
            hrs = int(data["uptime"]["system"]/3600)
            new_hb_device["uptime"] = f"{hrs}:{minutes:02d}:{sec:02d}"
        if "host" in data:
            new_hb_device["id"] = data["host"]
        
        new_hb_device["last_ping"] = datetime.now().strftime("%H:%M:%S, %d/%m/%Y")
        state, remark = state_calculator(device_cur_vals)
        new_hb_device['state'] = state
        new_hb_device['remark'] = remark
        new_hb_device['ping_status'] = 'alive'
        new_hb_device['state_colour'] = state_colours[state]
        if len(devices):
            for idx, listed_device in enumerate(devices): 
                if listed_device["id"] == new_hb_device["id"]:
                    # if the device id exists in the list, pop here and append it later                   
                    devices.pop(idx)  
        
        devices.append(new_hb_device)
        if device_table is not None:
            device_table.rows = devices
            device_table.update()
            show_summary_card.refresh()
        logger.debug(f"New hb: {new_hb_device}")    
    except Exception as e:
        logger.error(f"Failed to process new heartbeat: {e}")

@ui.refreshable
def show_summary_card():
    # refreshable function to update the summary card on top right
    with ui.row().classes('mx-5 w-full grid grid-cols-2 gap-2'):                
        ui.label(f'Online: {len([d for d in devices if d["ping_status"] == "alive"])}')
        ui.label(f'Offline: {len([d for d in devices if d["ping_status"] == "offline"])}')
        ui.label(f'Warnings: {len([d for d in devices if d["state"] == "Warning"])}')
        ui.label(f'Critical: {len([d for d in devices if d["state"] == "Critical"])}')
            
@ui.page('/')
def web_ui():     
    # landing page of the app    
    ui.add_css('''
        .health-table th { background-color: #e0e0e0; font-weight: bold;  text-align: center;}
        .health-table td { border: 1px solid #ddd; text-align: center;}
        .summary-box { background-color: #ffe6b3; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; }        
    ''')
    global device_table
    with ui.column().classes('w-full max-w-4xl mx-auto'):        
        with ui.row().classes('w-full items-center'): # Header
            with ui.column().classes('flex-grow'):
                ui.label('HEARBEAT MONITOR').classes('text-3xl')
                with ui.row().classes('w-full justify-start mt-10'):
                    search = ui.input(placeholder='Search term').classes('w-1/2').props('rounded outlined dense')                
            summary_card = ui.card().classes('summary-box ml-auto mt-10 w-1/3').props('flat')
            with summary_card:
                ui.label(f'Summary').classes('w-full text-center text-l font-bold')
                show_summary_card()

        device_table= ui.table(columns=[
            {'name': 'device_id', 'label': 'Device ID', 'field': 'id',},             
            {'name': 'last_ping', 'label': 'Last Ping', 'field': 'last_ping', 'sortable': True},
            {'name': 'uptime', 'label': 'Uptime', 'field': 'uptime', 'sortable': True},
            {'name': 'state', 'label': 'State', 'field': 'state_colour', 'sortable': True},
            {'name': 'info', 'label': 'More info', 'field': 'info'},
        ],
        rows=devices, pagination=8).classes('health-table w-full text-center').props('flat hoverable striped bordered')
       
        device_table.add_slot('body', r'''
            <q-tr :props="props">
                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                    <template v-if="col.name === 'info'">
                        <q-btn size="sm" color="accent" round flat
                            @click="props.expand = !props.expand"
                            :icon="props.expand ? 'remove' : 'add'" />
                    </template>
                    <template v-else>
                        {{ col.value }}
                    </template>
                </q-td>
            </q-tr>
            <q-tr v-show="props.expand" :props="props">
                <q-td colspan="100%">
                    <div class="text-left">Memory: {{props.row.mem_pct}}% CPU: {{props.row.cpu_thermal.current}} °C</div>
                            
                    <div class="text-right" v-if="props.row.state !== 'OK'">
                              {{props.row.state}}: {{ props.row.remark }}</div>
                </q-td>
            </q-tr>
        ''')
        search.bind_value(device_table, 'filter')
        
def main(rload=False):
    try:        
        parser = argparse.ArgumentParser()
        parser.add_argument("-t","--topic", type=str, default="heartbeats")
        parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
        )
        args = parser.parse_args()
        logger = logging.getLogger()
        logging.basicConfig(
            level=args.log_level.upper(),
            format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
            datefmt="%H:%M:%S",
        )

        client_broker = broker.Client("hb-mon-ui")
        client_broker.subscribe(args.topic, partial(new_device_hb,logger))
        ui.run(reload=rload, port=PORT, favicon='🩺', title='HB Monitor Dashboard')        

    except KeyboardInterrupt:        
        logger.info("Shutting down the app...")
        app.shutdown()
        return 0
    except Exception as e:
        logger.error(f"Error in main: {e}")
        app.shutdown()
        return -1        
    
if __name__ in {'__main__','__mp_main__'}:        
    main(rload=True)
    