/*
 * View model for OctoPrint-BedUsage
 *
 * Author: j7126
 * License: AGPLv3
 */
$(function () {
    function BedUsageViewModel(parameters) {
        var self = this;

        self.extruded_filament = ko.observable('-');
        self.extruded_filament_first_layer = ko.observable('-');
        self.lifetime_extruded_filament = ko.observable('-');
        self.lifetime_extruded_filament_first_layer = ko.observable('-');
        self.time_at_temp = ko.observable('-');
        self.lifetime_time_at_temp = ko.observable('-');

        var formatSeconds = function (secs) {
            secs = Math.round(secs)
            var hours = Math.floor(secs / 3600);
            var minutes = Math.floor((secs - (hours * 3600)) / 60);
            var seconds = secs - (hours * 3600) - (minutes * 60);

            if (hours < 10) { hours = "0" + hours; }
            if (minutes < 10) { minutes = "0" + minutes; }
            if (seconds < 10) { seconds = "0" + seconds; }
            return hours + 'h:' + minutes + 'm:' + seconds + 's';
        }

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin == "bedusage") {
                if (data.extruded_filament_first_layer) { self.extruded_filament_first_layer(Math.round(data.extruded_filament_first_layer)); }
                if (data.extruded_filament) { self.extruded_filament(Math.round(data.extruded_filament)); }
                if (data.lifetime_extruded_filament_first_layer) { self.lifetime_extruded_filament_first_layer(Math.round(data.lifetime_extruded_filament_first_layer)); }
                if (data.lifetime_extruded_filament) { self.lifetime_extruded_filament(Math.round(data.lifetime_extruded_filament)); }
                if (data.time_at_temp) { self.time_at_temp(formatSeconds(data.time_at_temp)); }
                if (data.lifetime_time_at_temp) { self.lifetime_time_at_temp(formatSeconds(data.lifetime_time_at_temp)); }
            }
        };

        self.onBeforeBinding = function () {

        };
    };

    // view model class, parameters for constructor, container to bind to
    OCTOPRINT_VIEWMODELS.push({
        construct: BedUsageViewModel,
        dependencies: ["temperatureViewModel", "printerStateViewModel", "printerProfilesViewModel", "connectionViewModel", "settingsViewModel", "displaylayerprogressViewModel", "controlViewModel", "gcodeViewModel", "enclosureViewModel", "loginStateViewModel"],
        optional: ["displaylayerprogressViewModel", "enclosureViewModel", "gcodeViewModel"],
        elements: ["#sidebar_plugin_bedusage", "#settings_plugin_bedusage"]
    });

});
