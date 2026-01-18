# Summary
Long range RC FPV crawler software stack. FPV video stream latency is sub-200ms when running on the 4G network.

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
`
gst-launch-1.0 rpicamsrc bitrate=1000000 sensor-mode=7 keyframe-interval=15 preview=false inline-headers=true \
   ! 'video/x-h264,width=640,height=480,framerate=48/1,profile=baseline' \
   ! h264parse \
   ! rtph264pay config-interval=1 pt=96 mtu=1200 \
   ! udpsink host=192.168.1.111 port=5000 sync=false async=false
`
This is optimized for Pi3/Pi4 hardware h.264 video encoder. This uses the legacy stack (and it is painful to get it working), as the modern one (libcamera) is a bit slower. On Pi 5 the libcamera would perform a bit slower than the legacy one, but on the Pi3/Pi4 - that's the better approach for low latency video stream.

To get the legacy video stack working a 32 bit OS (buster or bullseye) is required. On bullseye the legacy camera mode should be enabled and the rpicamsrc plugin needs to be built from the sources.

Video stream config for QGC: UDP h.264 stream on port 5000. Aspect ratio 1.33333. Try with the low latency video stream. If it doesn't work - switch to the non-low latency mode (and expect a bit more latency).


Progress:
1) Both services are up and running.
2) Logs are working and the RC link is receiving the commands.
3) Crawler to QGC link also works - the crawler correctly reports its location.
4) Crawler servos are working. There is failsafe applied if there are no RC commands in the last 2 seconds.
5) WireGuard link setup is automatically starting/stopping.
6) 4G stream to QGC works. The low latency check should be unchecked.
7) Switched to legacy camera stack for improved performance. Requires 32 bit buster/bullseye base OS + `rpicamsrc` GStreamer plugin.

What's next:
1) Add GPS support (ublox M10 module).
2) Add battery voltage monitoring.
3) Add buzzer with build in battery.