# HL7 Message Creator

A desktop GUI application for creating and editing healthcare HL7 messages, specifically designed for SIU (Scheduling Information Unsolicited) and ADT (Admit, Discharge, Transfer) message types.

**For detailed documentation, please visit:** [https://deepwiki.com/JMThomas00/HL7MessageCreator/1-overview](https://deepwiki.com/JMThomas00/HL7MessageCreator/1-overview)

## Overview

HL7 Message Creator is a comprehensive tool designed for healthcare IT professionals who need to generate and manage standardized HL7 messages for:

- Scheduling surgical procedures
- Managing patient admission, discharge, and transfer events
- Handling case event timelines (arrival, prep, in-room, completion, recovery, etc.)
- Testing HL7 interfaces and integrations

The application provides both creation and editing capabilities through an intuitive dual-mode interface, backed by CSV-based data sources for procedures, staff, surgeons, patients, and allergies.

## Features

### Creator Mode

- **Automated Patient Generation**: Generate complete patient records with random data
- **Procedure Browser**: Search and select from comprehensive surgical procedure database organized by specialty and category
- **Allergy Management**: Select and assign patient allergies for ADT messages
- **Staff Assignment**: Assign surgeons, circulators, scrub techs, CRNAs, and anesthesiologists
- **Multiple Message Types**:
  - Scheduled (S12): Single scheduling message
  - Scheduled & Case Events (S12 + S14): Scheduling plus complete surgical timeline
  - Scheduled & Canceled (S12 + S15): Scheduling with cancellation
- **Smart Date/Time Controls**: Quick-select buttons for common date/time adjustments
- **Live Preview**: Real-time HL7 message preview as you build
- **Multiple Patients**: Create and manage multiple patients in one session
- **Batch Export**: Save messages to organized folders (CurrentDay/NextDay/PreviousDay)

### Editor Mode

- **Bulk Editing**: Load and edit multiple HL7 files simultaneously
- **Structured Parsing**: Automatically parses HL7 segments into editable fields
- **Batch Updates**: Apply changes to single message or all loaded messages
- **Direct Edit**: Raw text editing mode for advanced users
- **Message Navigation**: Easily navigate between patients and message blocks
- **Validation**: Built-in HL7 format validation using hl7apy library

### User Experience

- **Dark Theme**: Modern, eye-friendly dark interface
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Responsive Design**: Dynamic window resizing
- **Search & Autocomplete**: Fast procedure and allergy lookup
- **Collapsible Panels**: Maximize workspace when needed

## Installation

### Quick Start (Recommended)

Simply run the provided batch file, which automatically handles all setup:

```batch
HL7MessageCreator.bat
```

This will:

1. Install Python 3.12 if not already present (using Windows Package Manager)
2. Create a virtual environment in `.venv`
3. Install the packages listed in `requirements.txt`
4. Launch the application

Do not copy or commit `.venv`. If that folder is broken, delete it and run the batch file again.

### Manual Installation

Use this on Linux or macOS, or on Windows when you do not want the batch file to install Python for you.

#### Prerequisites

- Python 3.11 or 3.12
- pip
- On Debian or Ubuntu, the `python3-venv` package: `sudo apt install python3-venv`

#### Steps

1. **Clone or download this repository**

2. **Create a virtual environment** in the project directory. Do not copy or commit `.venv`. If an older environment is broken, delete the folder and create it again.

   ```bash
   # Windows
   py -3.12 -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies** with the environment's own pip:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. **Run the application**:

   ```bash
   python HL7MessageCreator.py
   ```

## Usage

### Getting Started

1. **Launch the application** using `HL7MessageCreator.bat` or by running the Python script directly

2. **Choose your mode**:
   - Start in **Creator Mode** (default) to build new messages
   - Switch to **Editor Mode** (Ctrl+E or View → Editor) to modify existing files

### Creator Mode Workflow

1. **Create a New Patient** (Ctrl+N or File → New Patient)

2. **Fill Patient Details**:
   - Use "Random Full" for complete auto-population
   - Or manually enter: MRN, name, DOB, gender, etc.
   - Use date/time buttons for quick scheduling

3. **Select Procedures**:
   - Click "Browse Procedures" to open the procedure browser
   - Search by name or browse by specialty/category
   - Double-click to select, or use "Choose Random"
   - Add multiple procedures if needed

4. **Manage Allergies** (for ADT messages):
   - Click "Browse Allergies"
   - Select applicable allergies from the list
   - Selected allergies appear in the Allergies field

5. **Assign Staff**:
   - Use "Random Surgeon" and "Random Staff" for quick assignment
   - Or manually enter names and IDs
   - Add additional surgeons or staff members as needed

6. **Choose Message Type**:
   - **Scheduled**: Single S12 message
   - **Scheduled & Case Events**: S12 + complete surgical timeline (S14 events)
   - **Scheduled & Canceled**: S12 + S15 cancellation

7. **Generate Messages**:
   - Click "Create Patient" to generate HL7 messages
   - Review in the preview pane

8. **Save** (Ctrl+S):
   - Messages are saved to date-based folders
   - Filenames follow pattern: `{specialty}_{PatientName}_{MRN}_{MessageNumber}.hl7`

### Editor Mode Workflow

1. **Open Files** (Ctrl+O or File → Open File(s))
   - Select one or more .hl7 files
   - Files are grouped by patient

2. **Navigate Messages**:
   - Use Prev/Next Patient buttons to move between patients
   - Use Prev/Next Message buttons to move between messages within a patient

3. **Edit Fields**:
   - Modify any field in the structured editor
   - Changes appear in real-time preview

4. **Apply Changes**:
   - "Apply to Current": Updates only the displayed message
   - "Apply to All": Updates all messages for the current patient
   - Or use "Toggle Direct Edit" for raw text editing

5. **Save** (Ctrl+S):
   - Overwrites original files with modifications

## Keyboard Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `Ctrl+N` | New Patient (Creator mode only) |
| `Ctrl+O` | Open File(s) (Editor mode only) |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save & Exit |
| `Ctrl+Q` | Quit |
| `Ctrl+R` | Switch to Creator mode |
| `Ctrl+E` | Switch to Editor mode |
| `Tab` | Autocomplete procedure search |
| `Down Arrow` | Navigate procedure matches |
| `Enter` | Select highlighted procedure/allergy |

## Project Structure

```text
HL7MessageCreator/
├── HL7MessageCreator.py                      # Main application
├── HL7MessageCreator.bat                     # Automated setup and launcher
├── requirements.txt                          # Pinned runtime packages
├── requirements-dev.txt                      # Runtime packages plus PyInstaller
├── HL7MessageCreator.spec                    # PyInstaller build configuration
├── CLAUDE.md                                 # Developer documentation for Claude Code
├── README.md                                 # This file
│
├── Data Files (CSV - Required):
├── procedures.csv                            # Surgical procedures database
├── staff_names.csv                           # Staff member names and IDs
├── surgeon_names.csv                         # Surgeon names and IDs
├── patient_names.csv                         # Patient name pool for generation
└── allergies.csv                             # Allergy database for ADT messages
│
└── Output Folders (Auto-created):
    ├── CurrentDay/                           # Messages dated for today
    ├── NextDay/                              # Messages dated for tomorrow
    └── PreviousDay/                          # Messages dated for yesterday
```

## Dependencies

Runtime packages are pinned in `requirements.txt`. The batch file and the manual steps both install that file.

- **Python 3.11 or 3.12**: Application runtime
- **PyQt6 6.12.0**: GUI framework
- **hl7apy 1.3.5**: HL7 message parsing and validation
- **pandas 2.3.2**: CSV data handling and manipulation
- **numpy 2.2.1**: Numerical operations support
- **python-dateutil 2.9.0.post0**: Date/time parsing
- **pytz 2025.2**: Timezone handling

Development packages are in `requirements-dev.txt`:

- **PyInstaller 6.1.5**: Packaging Python apps as executables

## Data Files

The application requires CSV files in the same directory as the script:

### procedures.csv

Surgical procedure database with columns:

- `specialty`: Medical specialty (e.g., GEN, ORTHO, NEURO)
- `category`: Procedure category
- `procedure`: Procedure name
- `id`: Unique procedure identifier
- `description`: Detailed description
- `special_needs`: Special requirements or notes
- `cpt`: CPT code

### staff_names.csv

Staff member database with columns:

- `First Name`, `Last Name`, `ID`
- Used for Circulator, Scrub, CRNA, Anesthesiologist roles

### surgeon_names.csv

Surgeon database with columns:

- `First Name`, `Last Name`, `ID`

### patient_names.csv

Patient name pool with columns:

- `First Name`, `Last Name`
- Used for generating random test patients

### allergies.csv

Allergy database with columns:

- `allergy`: Allergy name (e.g., PENICILLIN, LATEX, SHELLFISH)
- Additional columns for severity, reaction type (if applicable)

## Building an Executable

To create a standalone Windows executable:

1. **Install the development packages** inside the virtual environment:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

2. **Build using the spec file**:

   ```bash
   pyinstaller HL7MessageCreator.spec
   ```

3. **Locate the executable**:

   - Built executable: `dist/HL7MessageCreatorFileView20.exe`
   - Ensure CSV data files are in the same directory as the executable

## HL7 Message Types

### SIU (Scheduling Information Unsolicited)

#### S12 - Notification of New Appointment Booking

- Used for scheduling new surgical procedures
- Contains patient demographics, procedure details, location, and staff assignments

#### S14 - Notification of Appointment Modification

- Used for case event updates (patient arrival, room entry, procedure start, etc.)
- Tracks surgical timeline with timestamps

#### S15 - Notification of Appointment Cancellation

- Used to cancel scheduled procedures

### ADT (Admit, Discharge, Transfer)

#### A01 - Admit/Visit Notification

- Used for patient admission events
- Includes patient allergies via AL1 segments

## Message Segments

Generated HL7 messages include:

- **MSH**: Message Header - message metadata and routing
- **SCH**: Schedule Activity Information - appointment scheduling details
- **PID**: Patient Identification - demographics
- **PV1**: Patient Visit - encounter information
- **OBX**: Observation/Result - case events and clinical observations
- **AIS**: Appointment Information - Service - procedure details
- **NTE**: Notes and Comments - procedure descriptions and special needs
- **AIL**: Appointment Information - Location - OR location
- **AIP**: Appointment Information - Personnel - staff assignments
- **AL1**: Patient Allergy Information - allergy details (ADT only)

## Troubleshooting

### Application won't start

- Ensure Python 3.11 or 3.12 is installed: `python --version`
- Check that all CSV files are present in the script directory
- Try running manually: `python HL7MessageCreator.py`

### "Failed to load CSV files" error

- Verify all required CSV files exist in the same directory as the script
- Check CSV file format and column headers
- Ensure files are not corrupted or empty

### Messages not saving

- Check write permissions for the script directory
- Ensure folder names don't conflict with existing files
- Verify disk space is available

### HL7 parsing errors in Editor mode

- Validate HL7 file format (proper segment separators)
- Check for non-standard segments or encoding
- Try opening files individually to isolate problematic messages

## Version History

### FileView24Allergies (Current)

- Added allergy browser and management
- Simplified interface focused on core functionality
- Improved ADT message generation with AL1 segments
- Streamlined timestamp formatting

### FileView20 (Previous)

- Environment-specific field mapping (US Demo vs UCH)
- Advanced clinical fields (ASA Score, Laterality, Anesthesia Type, Isolations)
- Complex segment routing logic
- Additional seconds precision in timestamps

## Contributing

This is a specialized healthcare IT tool. If you'd like to contribute:

1. Understand HL7 v2.5 message standards
2. Test thoroughly with various message types and patient scenarios
3. Maintain backward compatibility with existing CSV data formats
4. Follow the existing code style and patterns
5. Document any new features or fields added

## License

This project is provided for healthcare IT professionals to support HL7 interface development and testing. Please ensure compliance with HIPAA and other healthcare regulations when using with real patient data.

## Support & Documentation

- **Detailed Documentation**: [https://deepwiki.com/JMThomas00/HL7MessageCreator/1-overview](https://deepwiki.com/JMThomas00/HL7MessageCreator/1-overview)
- **HL7 Standards**: [HL7 International](https://www.hl7.org/)

## Acknowledgments

Built with Python and Tkinter for a modern, cross-platform desktop experience. Uses the hl7apy library for robust HL7 message parsing and validation.

---

**Important Note**: This tool is designed for testing and development purposes. Always validate generated messages against your specific HL7 implementation requirements before use in production environments.
