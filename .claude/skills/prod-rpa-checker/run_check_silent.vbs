Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "e:/AI/pythonProject/aiAutoTest"
WshShell.Run """e:\AI\pythonProject\aiAutoTest\.venv\Scripts\python.exe"" """E:\AI\pythonProject\aiAutoTest\.claude\skills\prod-rpa-checker\run_check.py""", 0, True
