import json
import logging
import environ
import argparse
from enum import IntEnum, Enum
from nicegui import ui, app, events
from fastapi import Request
from datetime import datetime
from functools import partial
from seguro.common import broker, config
from typing import TypedDict, Dict, Optional
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

env = environ.Env()
PORT = env.int("HB_MON_PORT", 9099)
# Interval in seconds.
HB_INTERVAL = env.int("HB_INTERVAL", 10)
# Thresholds to be flagged.
CRITICAL_PCT = env.int("CRITICAL_RESOURCE_PCT", 95)
WARNING_PCT = env.int("WARNING_RESOURCE_PCT", 75)
# Login credentials.
ENV_PASSWORD = env.int("HBMON_PSWD", "pass1")
ENV_USERNAME = env.int("HBMON_UNAME", "user1")
ENV_APPSECRET = env.int("HBMON_APPSECRET", "fdc8d08ab5c839582aa9")

EXPIRY_SECONDS = env.int("SESSION_EXPIRY_SEC", 200)


class Severity(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


class DevStatus(str, Enum):
    ALIVE = "alive"
    OFFLINE = "offline"
    ARCHIVED = "archived"


class CpuThermal(TypedDict):
    current: float
    critical: float


# Define TypedDict for new_hb_device structure.
class Device(TypedDict):
    mem_pct: float
    mem_available: float
    cpu_thermal: CpuThermal
    disk_pct: float
    uptime: str
    id: str
    last_ping: str
    state: str
    remark: str
    ping_status: str
    state_colour: str


devices: list[Device] = []
devices_unarchived: list[Device] = []
devices_archived: list[Device] = []
show_archived = False
device_hb_json_dict = {}

device_table = None
reauth_time = 0

state_colours = {
    "OK": "🟢",
    "Warning": "🟠",
    "Critical": "🔴",
}


class autoArchive_t(TypedDict):
    enable: bool
    interval: int


# Helper functions

auto_archive = {"enable": False, "interval": 0}
# Routes that don't require authentication.
unrestricted_page_routes = {"/login"}
logged_in = False


# Middleware to restrict access only to authenticated users.
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get("authenticated", False):
            if request.url.path not in unrestricted_page_routes:
                return RedirectResponse(
                    f"/login?redirect_to={request.url.path}"
                )

        return await call_next(request)


# Add middleware to the app
app.add_middleware(AuthMiddleware)


def update_device_state():
    if device_table:
        # devices_unarchived = list(devices)
        # devices_archived =[]
        time_now = datetime.now()
        pop_cnt = 0
        for idx, d in enumerate(devices):
            last_ping = datetime.strptime(d["last_ping"], "%H:%M:%S, %d/%m/%Y")
            time_diff = (time_now - last_ping).total_seconds()

            if time_diff > d["hb_interval"]:  # HB_INTERVAL:
                if d["id"] == "plink":
                    print(f" plink off {time_diff} hb:{d['hb_interval']} ")
                d["ping_status"] = (
                    "offline" if d["ping_status"] != "archived" else "archived"
                )
                if d["remark"]:
                    if "Offline" not in d["remark"]:
                        if d["state"] == "Warning":
                            d["remark"] = "Offline and Warnings"
                        else:
                            d["remark"] = d["remark"] + ", Offline"
                else:
                    d["remark"] = "Offline"

                d["state"] = "Critical"
                d["state_colour"] = state_colours["Critical"]

            if (
                time_diff > (auto_archive["interval"] + d["hb_interval"])
                and auto_archive["enable"]
            ):
                # print(f"Archiving {d}")
                d["ping_status"] = "archived"

        if show_archived:
            device_table.rows = [
                x for x in devices if x["ping_status"] == "archived"
            ]
        else:
            device_table.rows = [
                x for x in devices if x["ping_status"] != "archived"
            ]

        device_table.update()
        # print(f"Ref {devices}\n {devices_archived}\n  {devices_unarchived}\n----------")
        show_summary_card.refresh()


# Global timer to trigger the state update fn
app.timer(HB_INTERVAL, update_device_state, immediate=False)
severity = {"OK": 0, "Warning": 1, "Critical": 2}


def state_calculator(curr_vals: dict):
    '''
    Logic to calculate the maximum severity state and add remarks to
    be displayed per device on the web-ui.
    '''
    level = severity["OK"]
    state = "OK"
    remarks = ""
    # print(f"{type(severity["Critical"])} {int(severity["Critical"])}")
    for key, val in curr_vals.items():
        print(f"{key} {val}")
        # logic to find the highest severity[""] to be displayed
        if val >= CRITICAL_PCT:
            if level == severity["Critical"]:
                remarks += ", " + key
            else:
                remarks = key
            level = severity["Critical"]
            state = "Critical"
        elif val >= WARNING_PCT and level >= severity["OK"]:
            if level == severity["Warning"]:
                remarks += ", " + key
            else:
                remarks = key
            level = severity["Warning"]
            state = "Warning"

    return state, remarks


def new_device_hb(logger: logging.Logger, broker: any, msg: any):
    '''
    The callback fn triggered by the heartbeat to update the device params.
    '''
    global devices
    device_cur_vals: Dict[str, float] = {
        "Memory Usage": 0,
        "Disk Usage": 0,
        "CPU Temperature": 0,
    }
    try:
        new_hb_device: Device = {
            "mem_pct": 0.0,
            "mem_available": 0,
            "cpu_thermal": {"current": 0, "critical": 0},
            "disk_pct": 0,
            "uptime": "",
            "id": "",
            "last_ping": "",
            "state": "",
            "remark": "",
            "ping_status": "",
            "state_colour": "",
        }
        data = json.loads(msg.payload)

        if "memory" in data:
            new_hb_device["mem_pct"] = float(data["memory"]["percent"])
            new_hb_device["mem_available"] = data["memory"]["available"]
            device_cur_vals["Memory Usage"] = float(new_hb_device["mem_pct"])
        # if "cpu" in data:
        #     new_hb_device["cpu_freq"] = data["cpu"]["frequency"]["current"]
        if "sensors" in data:
            if "cpu_thermal" in data["sensors"]["temp"]:
                temp_data = data["sensors"]["temp"]["cpu_thermal"][0]
                new_hb_device["cpu_thermal"] = temp_data

                # Scaling the current temp to % to apply the logic uniformly
                scaled_temp_pct = (
                    100
                    * new_hb_device["cpu_thermal"]["current"]
                    / (new_hb_device["cpu_thermal"]["critical"] * 1.05)
                )
                device_cur_vals["CPU Temperature"] = scaled_temp_pct
        if "disks" in data and data["disks"] != []:
            for partitions in data["disks"]:
                if partitions["mountpoint"] == "/":
                    new_hb_device["disk_pct"] = partitions["usage"]["percent"]
                    device_cur_vals["Disk Usage"] = new_hb_device["disk_pct"]
        if "uptime" in data:
            sec = int(data["uptime"]["system"]) % 60
            minutes = int(data["uptime"]["system"] / 60) % 60
            hrs = int(data["uptime"]["system"] / 3600)
            new_hb_device["uptime"] = f"{hrs}:{minutes:02d}:{sec:02d}"
        if "host" in data:
            new_hb_device["id"] = data["host"]

        last_ping = datetime.now().strftime("%H:%M:%S, %d/%m/%Y")
        new_hb_device["last_ping"] = last_ping
        state, remark = state_calculator(device_cur_vals)
        new_hb_device["state"] = state
        new_hb_device["remark"] = remark
        new_hb_device["ping_status"] = "alive"
        new_hb_device["state_colour"] = state_colours[state]
        # new_hb_device["hb_interval"] = (
        #     0 if "hb_interval" not in data else data["hb_interval"]
        # )
        tmp_dev = []
        custom_hb_interval = (
            0 if "hb_interval" not in data else data["hb_interval"]
        )
        for x in devices:
            if x["id"] == new_hb_device["id"] and not custom_hb_interval:
                custom_hb_interval = x["hb_interval"]
            elif x["id"] != new_hb_device["id"]:
                tmp_dev.append(x)

        # devices = [x for x in devices if x["id"] != new_hb_device["id"]]
        devices = tmp_dev
        new_hb_device["hb_interval"] = (
            custom_hb_interval if custom_hb_interval else HB_INTERVAL
        )
        devices.append(new_hb_device)

        device_hb_json_dict[new_hb_device["id"]] = data  # msg.payload
        for x in devices:
            if x["id"] == new_hb_device["id"]:
                print(x)

        if device_table is not None:
            if show_archived:
                device_table.rows = [
                    x for x in devices if x["ping_status"] == "archived"
                ]
            else:
                device_table.rows = [
                    x for x in devices if x["ping_status"] != "archived"
                ]
            # device_table.rows = devices
            device_table.update()
            show_summary_card.refresh()
        logger.debug(f"New hb: {new_hb_device}")
    except Exception as e:
        logger.error(f"Failed to process new heartbeat: {e}")


# NiceGUI specific page builders


@ui.page("/login")
def login(redirect_to: str = "/") -> Optional[RedirectResponse]:
    def try_login() -> None:
        if password.value == ENV_PASSWORD and username.value == ENV_USERNAME:
            app.storage.user.update(
                {"username": username.value, "authenticated": True}
            )
            ui.navigate.to(redirect_to)
        else:
            ui.notify("Wrong username or password!")

    if app.storage.user.get("authenticated", False):
        return RedirectResponse("/")

    with ui.card().classes("w-1/4 absolute-center").props(
        "flat rounded bordered"
    ):
        with ui.column().classes("w-full gap-1 items-center"):
            ui.label("SEGuRo Platform").classes("text-2xl font-light")
            ui.label("Heartbeat Monitor Dashboard").classes(
                "text-2xl font-light"
            )
        with ui.column().classes("w-full items-center gap-4"):
            username = (
                ui.input("Username")
                .classes("w-3/4")
                .on("keydown.enter", try_login)
            )
            password = (
                ui.input("Password", password=True)
                .classes("w-3/4")
                .on("keydown.enter", try_login)
            )
        with ui.row().classes("w-full justify-center"):
            ui.button("Log in", on_click=try_login).props("flat bordered")


@ui.refreshable
def show_summary_card():
    ''' 
    Refreshable function to update the summary card on top right.
    '''
    with ui.row().classes("mx-8 w-full grid grid-cols-2 gap-2"):
        cnt = len([d for d in devices if d["ping_status"] == "alive"])
        ui.label(f"Online: {cnt}")
        cnt = len([d for d in devices if d["ping_status"] == "offline"])
        ui.label(f"Offline: {cnt}")
        cnt = len(
            [
                d
                for d in devices
                if d["state"] == "Warning" and d["ping_status"] != "archived"
            ]
        )
        ui.label(f"Warnings: {cnt}")
        cnt = len(
            [
                d
                for d in devices
                if d["state"] == "Critical" and d["ping_status"] != "archived"
            ]
        )
        ui.label(f"Critical: {cnt}")


class theme_button(ui.button):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state = False
        self.props("flat rounded color=black")
        self.on("click", self.toggle)


def handle_archive(event: events.GenericEventArguments):
    ui.notify(f"Archiving device: {event.args}")
    for d in devices:
        if d["id"] == event.args:
            d["ping_status"] = "archived"  # DevStatus.ARCHIVED
    print(devices)
    update_device_state()


def handle_view_json(event: events.GenericEventArguments):
    id = event.args
    # print(device_hb_json_dict)
    if id in device_hb_json_dict.keys():
        ui.navigate.to(f"/hb_json/{id}", new_tab=True)
    else:
        ui.notify("No saved HB")


@ui.page("/hb_json/{id}")
def render_json(id: str):
    ui.label(f"HB for device: {id}").classes("text-h6")
    pretty_json = json.dumps(device_hb_json_dict[id], indent=2)
    ui.code(pretty_json, language="json").style(
        "width: 100%; height: auto; overflow: visible; white-space: pre-wrap;"
    )


# auto_archive_cb = ui.checkbox()


@ui.page("/")
def web_ui():
    '''
    Landing page of the heartbeat monitor dashboard
    '''
    global auto_archive
    global show_archived

    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to("/login")

    async def handle_delete(event: events.GenericEventArguments):
        # print(f"Del {event.args}")
        global devices
        device_id = event.args
        delete_device = await dialog_del
        if delete_device:
            devices = [d for d in devices if d["id"] != device_id]
            ui.notify(f"Device {device_id} deleted from the list")
        # print(f"Delete dev {devices}")
        update_device_state()

    with ui.dialog().props() as dialog_del, ui.card():
        ui.label(f"Are you sure you want to delete the entry?")
        with ui.row().classes("w-full justify-end"):
            ui.button(
                "Delete", color="red", on_click=lambda: dialog_del.submit(True)
            ).classes("font-bold").props("flat bordered red")

    def set_show_archived(value: bool):
        global show_archived
        show_archived = value
        update_device_state()

    async def get_archive_interval(value: bool):
        # global auto_archive_time
        global auto_archive
        # app.storage.user.update({'auto_arch_state':value})
        if value:
            interval = await dialog_archive
            if isinstance(interval, float):
                # print(interval," ", type(interval))
                auto_archive["interval"] = interval
                auto_archive["enable"] = True
                global HB_INTERVAL
                HB_INTERVAL = min(HB_INTERVAL, auto_archive["interval"])
                ui.notify(
                    f'You chose {auto_archive["interval"]} sec(s) to archive inactive devices'
                )
                auto_archive_cb.value = True
            else:
                auto_archive_cb.value = False
        else:
            auto_archive["enable"] = False
            auto_archive_cb.value = False
        auto_archive_cb.update()

    with ui.dialog().props() as dialog_archive, ui.card():
        ui.label(
            "Enter the time (secs) after which an inactive device should be auto archived:  "
        )  # .style('justify-end')
        with ui.row().classes("w-full justify-end mb-3"):
            input_time = ui.number()
            with ui.column().classes("mt-3"):
                ui.button(
                    "Save",
                    on_click=lambda: (
                        dialog_archive.submit((input_time.value))
                        if isinstance(input_time.value, float)
                        else ui.notify(
                            f"Enter integer value for interval {type(input_time.value)}"
                        )
                    ),
                ).props("flat bordered").classes("font-bold")

    async def handle_custom_interval(event: events.GenericEventArguments):
        # print(f"Del {event.args}")
        global devices
        device_id = event.args
        hb_interval = await dialog_hb_interval
        if isinstance(hb_interval, float):
            for d in devices:
                if d["id"] == device_id:
                    d["hb_interval"] = hb_interval
                    break
            ui.notify(f"Device {device_id} HB interval updated")
        # print(f"Delete dev {devices}")
        update_device_state()

    with ui.dialog().props() as dialog_hb_interval, ui.card():
        ui.label(f"Set a custom HB interval (secs) for the device: ")
        with ui.row().classes("w-full justify-end mb-1"):
            interval_input = ui.number()
            with ui.column().classes("mt-3"):
                ui.button(
                    "Save",
                    on_click=lambda: (
                        dialog_hb_interval.submit((interval_input.value))
                        if isinstance(interval_input.value, float)
                        else ui.notify(
                            f"Enter integer value for interval {type(interval_input.value)}"
                        )
                    ),
                ).props("flat bordered").classes("font-bold")

        # with ui.row().classes("w-full justify-end"):
        #     ui.button(
        #         "Save", on_click=lambda: dialog_hb_interval.submit(True)
        #     ).classes("font-bold").props("flat bordered red")

    ui.add_css(
        """
        .health-table th { background-color: #e0e0e0;
                            font-weight: bold; text-align: center;}
        .health-table td { border: 1px solid #ddd; text-align: center;}
        .summary-box { background-color: #ffe6b3; padding: 10px;
                        margin-bottom: 10px; border: 1px solid #ccc; }
    """
    )

    with ui.column().classes("w-full max-w-4xl mx-auto"):
        with ui.row().classes("w-full items-center"):  # Header
            with ui.column().classes("flex-grow"):
                ui.label("Heartbeat Monitor").style(
                    "font-size: 45px;" "font-weight: 350;"
                )
            # with ui.column().classes('mt-5'):
            #     theme_button(icon="light_mode") #,on_click=lambda: dark.enable)
            # ui.button(icon='contrast').classes('bordered').props('flat rounded color=black')
            with ui.column().classes("mt-5"):
                ui.button(icon="logout", on_click=logout).props(
                    "flat rounded color=black"
                )
        with ui.row().classes("w-full justify-start mt-1 grid grid-cols-7"):
            with ui.column().classes("col-span-4 mt-5"):
                with ui.row().classes("w-full"):
                    search = (
                        ui.input(placeholder="Search term")
                        .classes("w-3/4")
                        .props("rounded outlined dense")
                    )
                with ui.row():
                    # ui.button('Auto Archive').props('rounded  color=black')
                    auto_archive_cb = ui.checkbox(
                        f"Auto Archive",
                        value=auto_archive["enable"],
                        on_change=lambda e: get_archive_interval(e.value),
                    )
                    ui.checkbox(
                        "Show Archived",
                        value=show_archived,
                        on_change=lambda e: set_show_archived(e.value),
                    )
                    # print("Auto "+str(auto_archive_time))
            with ui.column().classes("col-span-3"):
                summary_card = (
                    ui.card()
                    .classes("summary-box ml-auto w-3/4 ")
                    .props("flat")
                )
                with summary_card:
                    ui.label("Summary").classes(
                        "w-full text-center text-l font-bold"
                    )
                    show_summary_card()

        global device_table
        device_table = (
            ui.table(
                columns=[
                    {
                        "name": "device_id",
                        "label": "Device ID",
                        "field": "id",
                    },
                    {
                        "name": "last_ping",
                        "label": "Last Ping",
                        "field": "last_ping",
                        "sortable": True,
                    },
                    {
                        "name": "uptime",
                        "label": "Uptime",
                        "field": "uptime",
                        "sortable": True,
                    },
                    {
                        "name": "state",
                        "label": "State",
                        "field": "state_colour",
                        "sortable": True,
                    },
                    {"name": "info", "label": "More info", "field": "info"},
                ],
                rows=[],  # devices,
                pagination=8,
            )
            .classes("health-table w-full text-center")
            .props("flat hoverable striped bordered ")
        )
        global devices
        if devices:
            if show_archived:
                device_table.rows = [
                    x for x in devices if x["ping_status"] == "archived"
                ]
            else:
                device_table.rows = [
                    x for x in devices if x["ping_status"] != "archived"
                ]

        device_table.add_slot(
            "body",
            r"""
            <q-tr :props="props">
                <q-td v-for="col in props.cols"
                                    :key="col.name"
                                    :props="props">
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

            <!-- Render the expanded column with bg colour and buttons -->
            <q-tr v-show="props.expand" :props="props" class="expanded-row"
                :class="{'bg-green-1': props.row.state === 'OK',
                        'bg-orange-1': props.row.state === 'Warning',
                        'bg-red-1': props.row.state === 'Critical'}">
                <q-td colspan="100%">
                   <!-- Top row: values left, status right -->
                    <div class="flex justify-between items-center q-mb-sm">
                        <div>
                            Memory: {{ props.row.mem_pct }}% &nbsp;
                            CPU: {{ props.row.cpu_thermal.current }} °C
                        </div>
                        <div v-if="props.row.state !== 'OK'">
                            {{ props.row.state }}: {{ props.row.remark }}
                        </div>
                    </div>
                    <!-- Bottom row: buttons aligned right -->
                    <div class="flex justify-end gap-2">                    
                    <q-btn icon="data_object" color="pink-10" outline rounded padding="xs" size="sm" @click="() => $parent.$emit('view_json',props.row.id)" >
                        <q-tooltip class="bg-black">HB JSON</q-tooltip>
                    </q-btn>
                    <q-btn icon="update" color="black" outline rounded padding="xs" size="sm" @click="() => $parent.$emit('set_intvl',props.row.id)" >
                        <q-tooltip class="bg-black">Update HB interval</q-tooltip>
                    </q-btn>
                    <q-btn icon="archive" color="black" outline rounded padding="xs" size="sm" @click="() => $parent.$emit('archive',props.row.id)" >
                        <q-tooltip class="bg-black">Archive device</q-tooltip>
                    </q-btn>
                    <q-btn icon="delete" color="negative" outline rounded padding="xs" size="sm" @click="() => $parent.$emit('delete',props.row.id)" >
                        <q-tooltip class="bg-negative">Delete device</q-tooltip>
                    </q-btn>
                    </div>
                </q-td>
            </q-tr>
        """,
        )
        # indigo-10
        device_table.on("view_json", handle_view_json)
        device_table.on("set_intvl", handle_custom_interval)
        device_table.on("archive", handle_archive)
        device_table.on("delete", handle_delete)

        search.bind_value(device_table, "filter")


def main(rload=False):
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--topic", type=str, default="heartbeats")
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
            format=(
                "%(asctime)s.%(msecs)03d " "%(levelname)s %(name)s %(message)s"
            ),
            datefmt="%H:%M:%S",
        )

        client_broker = broker.Client("hb-mon-ui")
        client_broker.subscribe(args.topic, partial(new_device_hb, logger))
        ui.run(
            reload=rload,
            port=PORT,
            favicon="🩺",
            title="HB Monitor Dashboard",
            storage_secret=ENV_APPSECRET,
        )

    except KeyboardInterrupt:
        logger.info("Shutting down the app...")
        app.shutdown()
        return 0
    except Exception as e:
        logger.error(f"Error in main: {e}")
        app.shutdown()
        return -1


if __name__ in {"__main__", "__mp_main__"}:
    main(rload=True)
