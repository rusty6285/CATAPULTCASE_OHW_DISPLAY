# CATAPULTCASE_OHW_DISPLAY
CATAPULTCASE_OHW_DISPLAY


Requirements:
- Lilygo T-Display S3 AMOLED (https://www.lilygo.cc/products/t-display-s3-amoled)
- Windows 11
- Openhardwaremonitor-v0.9.6

Current issues:
- There can be an initial delay in GPU temperature displaying, this is due to additional logic to validate the data
- The CPU fan speed is not read in this initial release

Setup:
1. Update the python script to use the COM port of your connected Lilygo display (defaults to COM5)
2. Compile (or use the pre-compiled bin file provided) and flash to the Lilygo display
3. Connect the Lilygo display and you should see the splash screen
   
![screenshot](splash.jpg)

5. Start openhardwaremonitor-v0.9.6
6. Start the python script and the metrics should appear on Lilygo display

![screenshot](running.jpg)
