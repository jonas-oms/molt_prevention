# MQTT Publisher

You have to create your own config.h file. 

This is an example how the file could look like:

#ifndef CONFIG_H
#define CONFIG_H

const char* ssid = "your-ssid";
const char* password = "your-password";
const char* mqtt_server = "your-mqtt-server";
const char* mqtt_user = "your-mqtt-username";
const char* mqtt_password = "your-mqtt-password";

#endif // CONFIG_H
