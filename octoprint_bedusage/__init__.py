# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin
from octoprint.access.users import AnonymousUser
from octoprint.events import Events
import re
import os
import time
import sqlite3
from octoprint.util import RepeatedTimer


class Database:
    db_version = 1

    def __init__(self, data_path, _settings, logger):
        self._settings = _settings
        self.data_path = data_path
        self._logger = logger

        self.db_file = os.path.join(self.data_path, "bedusage.db")
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()

        #self.version = 0
        #self.dbc.execute('''DROP TABLE stats''')

        if self.version == 0:
            self.version = self.db_version
            dbc.execute('''CREATE TABLE stats
             (extruded_filament REAL, extruded_filament_first_layer REAL, time_at_temp REAL)''')
            dbc.execute("INSERT INTO stats VALUES (0, 0, 0)")
            db.commit()
        elif self.version != self.db_version:
            self.migrate(self.version, self.db_version)

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    @property
    def version(self):
        return self._settings.get(["db_version"])

    @version.setter
    def version(self, v):
        self._settings.set(["db_version"], v)
        self._settings.save()

    def migrate(self, old, new):
        while old < new:
            old += 1
            self._migrate(old)
        self.version = new

    def _migrate(self, new):
        if new == 1:
            return

    @property
    def extruded_filament(self):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute("SELECT extruded_filament FROM stats")
        v = dbc.fetchone()['extruded_filament']
        del dbc
        del db
        return v

    @extruded_filament.setter
    def extruded_filament(self, v):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute("UPDATE stats SET extruded_filament = ? LIMIT 1", (v,))
        db.commit()
        del dbc
        del db

    @property
    def extruded_filament_first_layer(self):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute("SELECT extruded_filament_first_layer FROM stats")
        v = dbc.fetchone()['extruded_filament_first_layer']
        del dbc
        del db
        return v

    @extruded_filament_first_layer.setter
    def extruded_filament_first_layer(self, v):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute(
            "UPDATE stats SET extruded_filament_first_layer = ? LIMIT 1", (v,))
        db.commit()
        del dbc
        del db

    @property
    def time_at_temp(self):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute("SELECT time_at_temp FROM stats")
        v = dbc.fetchone()['time_at_temp']
        del dbc
        del db
        return v

    @time_at_temp.setter
    def time_at_temp(self, v):
        db = sqlite3.connect(self.db_file)
        db.row_factory = self.dict_factory
        dbc = db.cursor()
        dbc.execute(
            "UPDATE stats SET time_at_temp = ? LIMIT 1", (v,))
        db.commit()
        del dbc
        del db


class BedUsagePlugin(octoprint.plugin.SettingsPlugin,
                     octoprint.plugin.StartupPlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.EventHandlerPlugin):

    extruded_filament = 0.0
    extruded_filament_temp = 0.0
    extruded_filament_first_layer = 0.0
    extruded_filament_first_layer_temp = 0.0

    at_temp = False
    at_temp_start_time = None
    current_layer = 0
    extruder_mode = ""

    def initialize(self):
        self.db = Database(self.get_plugin_data_folder(),
                           self._settings, self._logger)
        self.message_old = self.get_message()

    # ~~ StartupPlugin mixin
    def on_after_startup(self):
        self._logger.info("Bed Usage plugin started")
        # timer
        self.timer = RepeatedTimer(
            1.0, self.send_notifications, run_first=True)
        self.timer.start()

    def get_message(self):
        return dict(extruded_filament=self.extruded_filament,
                    extruded_filament_first_layer=self.extruded_filament_first_layer,
                    lifetime_extruded_filament=self.db.extruded_filament,
                    lifetime_extruded_filament_first_layer=self.db.extruded_filament_first_layer,
                    time_at_temp=0 + (time.time() - self.at_temp_start_time) if self.at_temp else 0,
                    lifetime_time_at_temp=self.db.time_at_temp + ((time.time() - self.at_temp_start_time) if self.at_temp else 0))

    def send_notifications(self):
        self.db.extruded_filament += self.extruded_filament_temp
        self.extruded_filament += self.extruded_filament_temp
        self.extruded_filament_temp = 0.0
        self.extruded_filament_first_layer += self.extruded_filament_first_layer_temp
        self.db.extruded_filament_first_layer += self.extruded_filament_first_layer_temp
        self.extruded_filament_first_layer_temp = 0.0
        try:
            if self._printer.get_current_temperatures()['bed']['target'] != 0.0:
                if not self.at_temp:
                    self.at_temp_start_time = time.time()
                    self.at_temp = True
            elif self.at_temp == True:
                self.db.time_at_temp += time.time() - self.at_temp_start_time
                self.at_temp_start_time = None
                self.at_temp = False
        except:
            self.at_temp_start_time = None
            self.at_temp = False
        message = self.get_message()
        # to save bandwidth, only send message if there is a change
        if message != self.message_old:
            self._plugin_manager.send_plugin_message(self._identifier, message)
            self.message_old = message

    def socket_authed_hook(self, socket, user, *args, **kwargs):
        if not isinstance(user, AnonymousUser):
            message = self.get_message()
            self._plugin_manager.send_plugin_message(self._identifier, message)

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self.extruded_filament = 0.0
            self.extruded_filament_first_layer = 0.0
            self.current_layer = 0
            self.extruder_mode = ""
            message = self.get_message()
            self._plugin_manager.send_plugin_message(self._identifier, message)

    # ~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
            db_version=0
        )

    # def on_settings_save(self, data):
    #    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def get_template_configs(self):
        return [
            dict(type="sidebar", custom_bindings=True, icon="bed"),
            dict(type="settings", custom_bindings=True)
        ]

    # ~~ AssetPlugin mixin
    def get_assets(self):
        return dict(
            js=["js/bedusage.js"],
            less=["less/bedusage.less"]
        )

    # ~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            bedusage=dict(
                displayName="Bed Usage Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="j7126",
                repo="OctoPrint-BedUsage",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/j7126/OctoPrint-BedUsage/archive/{target_version}.zip"
            )
        )

    def process_gcode(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if not gcode:
            return

        # we only actually need to process this if we are still on the first layer
        if self.current_layer <= 1:
            # processing layer change
            # cura
            if re.match('^;LAYER:([0-9]+)', cmd):
                self.current_layer += 1
            # Simplify3D
            elif re.match('^; layer ([0-9]+)', cmd):
                self.current_layer += 1
            # Slic3r/PrusaSlicer
            elif re.match('^;BEFORE_LAYER_CHANGE', cmd):
                self.current_layer += 1
            # Already preprocessed by dashboard
            elif re.match('^M117 DASHBOARD_LAYER_INDICATOR', cmd):
                self.current_layer += 1
            # Already preprocessed by DisplayLayerProgress
            elif re.match('^M117 INDICATOR-Layer', cmd):
                self.current_layer += 1

        if gcode in ("M82"):
            self.extruder_mode = "absolute"

        elif gcode in ("M83"):
            self.extruder_mode = "relative"

        elif gcode in ("G90"):
            self.extruder_mode = "absolute"

        elif gcode in ("G91"):
            self.extruder_mode = "relative"

        elif gcode in ("G0", "G1"):
            CmdDict = dict((x, float(y)) for d, x, y in (
                re.split('([A-Z])', i) for i in cmd.upper().split()))
            if "E" in CmdDict:
                e = float(CmdDict["E"])
                if self.extruder_mode == "absolute":
                    a = e - self.extruded_filament - self.extruded_filament_temp
                elif self.extruder_mode == "relative":
                    a = e
                else:
                    return

                if self.current_layer != 0:
                    self.extruded_filament_temp += a
                # only if it is the first layer
                if self.current_layer == 1:
                    self.extruded_filament_first_layer_temp += a

        else:
            return


__plugin_name__ = "Bed Usage"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = BedUsagePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.queued": __plugin_implementation__.process_gcode,
        "octoprint.server.sockjs.authed": __plugin_implementation__.socket_authed_hook
    }

    global __plugin_settings_overlay__
    __plugin_settings_overlay__ = dict(appearance=dict(components=dict(order=dict(sidebar=["connection",
                                                                                           "state",
                                                                                           "plugin_bedusage",
                                                                                           "files"]))))
