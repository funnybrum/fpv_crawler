# Summary
Long range RC FPV crawler software stack.

The setup is:
Robot side is a 1:10 crawler with Raspberry Pi 3B (or newer). For PWM control it uses Arduino Pro Mini connected via the UART and running FirmataStandard firmware on it. The video stream will be coming from analog camera connected to a USB port on the Pi. The camera will be mounted on 3 axis gimbal that will enable the operator to look at left and right.

For 4G connectivity the Pi as a Huawei E3372h dongle attached.

Control station is QGC paired with RadioMaster controller over BLE.

What has been tested:
* FPV video link latency over 4G network is around 200-2500 milliseconds. QGC can show the video stream. This is with the Pi v1 camera connected to the CSI port.
* QGC can use RadioMaster controllers with ELRS via BLE connection. Control link latency is expected to be below 100ms.
* The Pi3B is sufficient for the setup.

Firmata Setup:
The crawler uses an Arduino Pro Mini running the StandardFirmata firmware to control the steering and throttle servos. The Arduino is connected to the Raspberry Pi via the first UART port.
* Steering: Pin 5
* Throttle: Pin 6

GStreamer command for the crawler side:
gst-launch-1.0 libcamerasrc ! video/x-raw,width=640,height=480,framerate=30/1 ! videoconvert ! v4l2h264enc extra-controls="controls,video_bitrate=1500000,h264_profile=0,h264_i_frame_period=30" ! 'video/x-h264,level=(string)4' ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=192.168.1.111 port=5000 sync=false async=false


Video stream config for QGC: UDP h.264 stream on port 5000. Aspect ratio 1.33333


Progress:
1) Both services are up and running.
2) Logs are working and the RC link is receiving the commands.
3) Crawler to QGC link also works - the crawler correctly reports its location.
4) Crawler servos are working.
5) WireGuard link setup is automatically starting/stopping.
6) 4G stream to QGC works. The low latency check should be unchecked.

TODOs:
1) Failsafe the servos to 1500
