# CATAPULTCASE_OHW_DISPLAY
CATAPULTCASE_OHW_DISPLAY


Requirements:
- Lilygo T-Display S3 AMOLED (https://www.lilygo.cc/products/t-display-s3-amoled)
- Windows 11
- Openhardwaremonitor-v0.9.6

Current issues:
- The CPU fan speed is not read in this initial release

Setup:
1. Compile the contents of GUI_Python_Code folder by running PyInstaller in the directory with all files present, using the CC_HW_GUI.spec configuration file
3. Compile the contents of Arduino_Code folder and flash to the Lilygo display 
4. Connect the Lilygo display and you should see the splash screen
   
![screenshot](splash.jpg)

5. Start openhardwaremonitor-v0.9.6
6. Run the compiled CC_HW_GUI.exe and configure using the GUI.

![screenshot](GUI.jpg)

Press the 'START" button and the metrics should start to feed the LilyGo display

![screenshot](running.jpg)
