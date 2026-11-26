[Setup]
AppId=AccordionTuningLab
AppName=Accordion Tuning Lab
AppVersion=3.4
DefaultDirName={localappdata}\Programs\Accordion Tuning Lab
DefaultGroupName=Accordion Tuning Lab
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Accordion_Tuning_Lab_Setup
SetupIconFile=Accordion.ico
UninstallDisplayIcon={app}\Accordion_Tuning_Lab.exe
Compression=lzma2
SolidCompression=yes
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
[Files]
Source: "dist\Accordion_Tuning_Lab.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Accordion Tuning Lab"; Filename: "{app}\Accordion_Tuning_Lab.exe"
Name: "{userdesktop}\Accordion Tuning Lab"; Filename: "{app}\Accordion_Tuning_Lab.exe"
