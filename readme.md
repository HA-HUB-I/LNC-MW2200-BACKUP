# LNC MW2200A CNC Controller Configuration

## Directory Overview

This directory contains a backup of the configuration and data files for an LNC MW2200A CNC controller. These files define the machine's parameters, HMI (Human-Machine Interface) layout, PLC (Programmable Logic Controller) logic, and other settings.

## Key Files

*   **`disk2/hmi/language_def/`**: Contains language files for the HMI. The `.str` files map UI element IDs to text in different languages.
*   **`disk3/data/open_custom_bottom/` and `disk3/data/open_extend_1/`**: These directories contain files that define the HMI layout, including images (`.png`), UI structure (`ohframe.xml`), and language strings (`.str`).
*   **`disk3/data/log/`**: Contains log files, such as `cncsys.txt` (system log) and `opmsg.txt` (operation messages).
*   **`disk4/machine/`**: This is the most critical directory, containing the core machine configuration files:
    *   **`param_define.txt`**: Defines the machine parameters, including their names, types, and valid ranges.
    *   **`param.txt`**: A text file listing the machine parameters and their current values.
    *   **`cnc.lpar`**: A binary file that likely stores the machine parameters in a more compact format.
    *   **`plc.prj`**: The project file for the PLC, which controls the machine's logic.
    *   **`keymap.ini`**: Defines the mapping of physical keys on the control panel to their functions.
    *   **`cnc_plc_*.str` and `hmi*.str`**: String files for different parts of the system.

## Usage

These files are intended for technicians and engineers who need to restore, modify, or troubleshoot the LNC MW2200A CNC controller.

*   **To restore the machine's configuration**, you would typically use the LNC software to load the files from these directories onto the controller.
*   **To modify the machine's parameters**, you can edit `param.txt` and then load it onto the controller. It is also possible to edit the parameters directly on the machine's HMI.
*   **To customize the HMI**, you can edit the `ohframe.xml` files and the associated images and string files.
*   **To modify the PLC logic**, you would need the appropriate LNC software to open and edit the `plc.prj` file.

## Keymap Configuration

Here's how to add new quick F vacuum/aspiration buttons:


   1. Identify the M-code. For example:
   2. Create a macro in `ohframe.xml`: Open the file disk3\data\open_custom_bottom\ohframe.xml (or the other ohframe.xml if the button is for another
      page) and add a new <Macro> entry in the <MacroList> section. The macro will execute the corresponding M-code.
  `xml
      <Macro Name="VacuumPump1On" Comment="Switch on vacuum pump 1">
          <Code>M(10);</Code>
          <Code>RET</Code>
      </Macro>
      `
      Example for macro "Vacuum pump 1 Off":
      `xml
      <Macro Name="VacuumPump1Off" Comment="Switching off vacuum pump 1">
          <Code>M(11);</Code>
          <Code>RET</Code>
      </Macro>
      `
      Example for macro "Dust Lid Lifting":
  `xml
      <Macro Name="DustCoverUp" Comment="Lifting the dust cover">
          <Code>M(140);</Code>
          <Code>RET</Code>
      </Macro>
      `


   3. In the same ohframe.xml file, add a new <QohButton> (or <QohLabel>) element at the desired location in the HMI page.
   1. Backup: Always back up ohframe.xml and any associated .str files before making changes.
   * VACUUM PUMP 1 ON: M10

**Caution:**  Please use extreme caution when modifying these files, as incorrect changes can cause the machine to malfunction. Always
  consult the official LNC documentation for your specific controller model.



**Caution:** Modifying these files without a thorough understanding of the LNC controller can lead to machine malfunction or damage. Always back up the original files before making any changes.


Moving from an LNC MW2200A controller to Mach3 is not just a software adjustment, but a significant change that requires:


   1. Hardware replacement. For Mach3, a compatible motion control board will be required (e.g. SmoothStepper, UC100) and possibly rewiring to the motor and sensor drivers.
  Is it necessary? If the LNC controller is working correctly and meets your needs, switching to Mach3 is optional. It is usually done for specific
   functionality requirements, preferences for the Mach3 interface, or when there are problems with the existing controller. This is a major undertaking that requires
  in-depth knowledge of electronics and CNC systems.

## Complete to backup.tgz

To create a complete backup of the configuration files, you can use the following command:

```bash
tar -czvf backup.tgz disk1/ disk2/ disk3/ disk4/
```

This command will create a compressed archive named `backup.tgz` containing all the files from the specified directories.

## USB restore instructions
To restore the configuration files to the LNC MW2200A CNC controller using a USB drive, follow these steps:
1. **Prepare the USB Drive**:
   - Format a USB drive to FAT32 to ensure compatibility with the LNC controller.
   - Copy the backup files (e.g., `backup.tgz`) to the root directory of the USB drive.
2. **Change User Permissions Userlevel 5**
   - from the main screen, press the "User" button to change the user level to "Admin" or "Service" to gain access to system settings.
3. **Access the File Management Menu**:
   - Navigate to the "File Management" section in the system settings.
4. **Insert the USB Drive**:
   - Insert the prepared USB drive into the USB port on the LNC MW2200A CNC controller.
   - Press the emergency stop button.
5. **Backup before Restore**:
   - Before restoring, it is advisable to back up the current configuration. Use the file management menu to copy the existing configuration files to another location on the controller or to another USB drive.

![Backup and Restore](backup_restore.jpg)

## Modbus TCP Web Interface

A Python/Flask web dashboard that communicates with the LNC controller over
its built-in Modbus TCP server (port 502). It shows real-time machine status,
axis positions, spindle/feed data and lot counters, and lets operators issue
commands from any browser on the local network.

See **[modbus_web/README.md](modbus_web/README.md)** for full setup and usage instructions.

```bash
cd modbus_web
pip install -r requirements.txt
MODBUS_HOST=<controller-ip> python app.py
# then open http://localhost:5000
```

![Modbus Dashboard](https://github.com/user-attachments/assets/9760c33b-bb0e-4932-a6a5-723ccc3b055f)

[Telegram Group](https://t.me/lnc_mw2200a)
[YouTube Channel](https://www.youtube.com/@lnc_mw2200a)