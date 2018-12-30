[![build status](http://img.shields.io/travis/robmarkcole/Hue-sensors-HASS/master.svg?style=flat)](https://travis-ci.org/robmarkcole/Hue-sensors-HASS)
[![Coverage Status](https://coveralls.io/repos/github/robmarkcole/Hue-sensors-HASS/badge.svg?branch=master)](https://coveralls.io/github/robmarkcole/Hue-sensors-HASS?branch=master)

# Hue-sensors-HASS
[FOR COMMUNITY SUPPORT PLEASE USE THIS THREAD](https://community.home-assistant.io/t/hue-motion-sensors-remotes-custom-component)

Component for Hue sensors in Home-Assistant, **updated for 0.66 to be independent of the Hue hub platform**.

Place the custom_components folder in your configuration directory (or add its contents to an existing custom_components folder). You need to set up [Hue bridge](https://www.home-assistant.io/components/hue/) first.

Hue dimmer remotes can be used for a click and long press (hold button for 2 sec and see LED blink twice).

```
device_tracker:
  - platform: hue
sensor:
  - platform: hue
```

As per [this issue](https://github.com/robmarkcole/Hue-sensors-HASS/issues/48) it is recommended to use the default naming options in the Hue app in order to ensure sensible sensor names in HA.

## Front end display

To add the following group to your HA frontend, add the following to groups.yaml (obviously editing to use your sensors):

```
default_view:
  view: yes
  entities:
    - group.Hue

Hue:
  entities:
    - sensor.bedroom_motion_sensor
    - sensor.hall_motion_sensor
    - sensor.living_room_motion_sensor
    - sensor.living_room_temperature
    - sensor.living_room_light_level
    - sensor.living_room_lux
    - sensor.living_room_remote
    - sensor.remote_bedroom
    - sensor.robins_iphone
```

Temperature, light level and other data in the sensor attributes can be broken out into their own sensor using a template sensor, for example:

```
- platform: template
  sensors:

    living_room_temperature:
      friendly_name: 'Living room temperature'
      value_template: '{{states.sensor.living_room_motion_sensor.attributes.temperature}}'
      unit_of_measurement: °C

    living_room_light_level:
      friendly_name: 'Living room light level'
      value_template: '{{states.sensor.living_room_motion_sensor.attributes.lx}}'
      unit_of_measurement: lux
```

<p align="center">
<img src="https://github.com/robmarkcole/Hue-sensors-HASS/blob/master/hue.png" width="500">
</p>

## Track Updates
This custom component can be tracked with the help of [custom-lovelace](https://github.com/ciotlosm/custom-lovelace).

In your configuration.yaml

 ```
custom_updater:
 component_urls:
   - https://raw.githubusercontent.com/robmarkcole/Hue-sensors-HASS/master/custom_updater.json
```

## Debugging

If you get an error when using this component, the procedure for debugging is as follows.

1. Open an issue here on Github. Include the error message, release number of the custom component.
2. Download the Hue API response following the instructions [here](https://www.hackster.io/robin-cole/hijack-a-hue-remote-to-control-anything-with-home-assistant-5239a4#toc-hue-api-1). Save into a .json file.
3. Parse the json file using the [hue_sensors package](https://pypi.python.org/pypi/hue-sensors/1.2) and report the device ID (e.g. RWL_06-02) that is causing your issue.

There are a couple of examples of this process in the debugging_issues folder.
