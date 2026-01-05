The idea behind this project is to create an FPV crawler that is 4G connected. Check the README.md for further details.

Client side will be QGroundControl + RC controller (Radiomaster ELRS model connected to the computer as BLE controller). QGC will forward controller commands to the crawler.


Crawler will use a Raspberry Pi 3B (or Pi 5 later on, but for now consider just hte Pi3B) and will:
1) Exposed video stream by running gstreamer as service. Camera is CSI port connected. Video stream aims at low latency and limited bandwith.
2) Expose PWM controls to the servo motors of the crawler. This is done vis https://github.com/firmata/arduino/tree/main/examples/StandardFirmata flashed on Arduino Pro Mini connected to the Pi first UART port.


Crawler 4G connectivity is not in the scope of this project. It uses Huawei e3372h dongle connected to the Pi's USB port. There is also WireGuard connectivity setted up on the Pi.


Rules for Gemini CLI tool:
1) Limit your work to the project folder here.
2) Do not touch the git repo. I'll review the code and commit when needed.
3) Always reload the files before processing a message in the chat. The code is being reviewed and updated in parallel.