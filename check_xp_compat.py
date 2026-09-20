#!/usr/bin/env python3
"""
Scan a Windows PE binary (.exe or .dll) for APIs and DLLs incompatible with Windows XP (NT 5.1).
Usage:
    python3 check_xp_compat.py path/to/openrct2.exe
"""

import sys
import re
import subprocess
import shutil

# Known DLLs that do not exist on Windows XP
INCOMPATIBLE_DLLS = {
    "bcrypt.dll": "Windows Vista",
    "ncrypt.dll": "Windows Vista",
    "d3d10.dll": "Windows Vista",
    "d3d10_1.dll": "Windows Vista SP1",
    "d3d11.dll": "Windows 7",
    "dxgi.dll": "Windows Vista",
    "dwmapi.dll": "Windows Vista",
    "uxtheme.dll": "Windows XP (OK)", # OK on XP
    "api-ms-win-": "Windows 7 / 8 / 10 (Universal CRT / ApiSet)",
    "ext-ms-win-": "Windows 8 / 10",
}

# Known APIs introduced in Windows Vista or later
VISTA_PLUS_APIS = {
    # Synchronization & Condition Variables (Vista)
    "InitializeConditionVariable": "Windows Vista",
    "SleepConditionVariableCS": "Windows Vista",
    "SleepConditionVariableSRW": "Windows Vista",
    "WakeConditionVariable": "Windows Vista",
    "WakeAllConditionVariable": "Windows Vista",
    "InitializeSRWLock": "Windows Vista",
    "AcquireSRWLockExclusive": "Windows Vista",
    "AcquireSRWLockShared": "Windows Vista",
    "ReleaseSRWLockExclusive": "Windows Vista",
    "ReleaseSRWLockShared": "Windows Vista",
    "TryAcquireSRWLockExclusive": "Windows Vista",
    "TryAcquireSRWLockShared": "Windows Vista",
    "InitOnceExecuteOnce": "Windows Vista",
    "InitOnceInitialize": "Windows Vista",
    "InitOnceBeginInitialize": "Windows Vista",
    "InitOnceComplete": "Windows Vista",

    # Time & Tick (Vista)
    "GetTickCount64": "Windows Vista",

    # I/O & File Management (Vista)
    "CancelIoEx": "Windows Vista",
    "CancelSynchronousIo": "Windows Vista",
    "CreateSymbolicLinkW": "Windows Vista",
    "CreateSymbolicLinkA": "Windows Vista",
    "GetFinalPathNameByHandleW": "Windows Vista",
    "GetFinalPathNameByHandleA": "Windows Vista",
    "SetFileInformationByHandle": "Windows Vista",
    "GetFileInformationByHandleEx": "Windows Vista",
    "OpenFileById": "Windows Vista",

    # NLS / Locale Extensions (Vista)
    "CompareStringEx": "Windows Vista",
    "GetDateFormatEx": "Windows Vista",
    "GetTimeFormatEx": "Windows Vista",
    "GetLocaleInfoEx": "Windows Vista",
    "LCMapStringEx": "Windows Vista",
    "ResolveLocaleName": "Windows Vista",
    "GetUserDefaultLocaleName": "Windows Vista",
    "GetSystemDefaultLocaleName": "Windows Vista",
    "EnumCalendarInfoExEx": "Windows Vista",
    "EnumDateFormatsExEx": "Windows Vista",
    "EnumSystemLocalesEx": "Windows Vista",
    "EnumTimeFormatsExEx": "Windows Vista",
    "IsValidLocaleName": "Windows Vista",
    "NormalizeString": "Windows Vista",
    "IsNormalizedString": "Windows Vista",

    # Memory & Process (Vista / 7)
    # Note: K32* functions moved from psapi.dll to kernel32.dll in Windows 7
    "K32GetProcessMemoryInfo": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "K32EnumProcesses": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "K32EnumProcessModules": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "K32GetModuleFileNameExW": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "K32GetModuleFileNameExA": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "K32GetModuleInformation": "Windows 7 (in kernel32; use psapi.dll on XP)",
    "GetLogicalProcessorInformationEx": "Windows 7",

    # Registry (Vista)
    "RegDeleteTreeW": "Windows Vista",
    "RegDeleteTreeA": "Windows Vista",
    "RegSetKeyValueW": "Windows Vista",
    "RegSetKeyValueA": "Windows Vista",
    "RegDeleteKeyValueW": "Windows Vista",
    "RegDeleteKeyValueA": "Windows Vista",
    "RegCopyTreeW": "Windows Vista",
    "RegCopyTreeA": "Windows Vista",

    # Event Tracing (Vista)
    "EventRegister": "Windows Vista",
    "EventUnregister": "Windows Vista",
    "EventWrite": "Windows Vista",
    "EventWriteTransfer": "Windows Vista",
    "EventActivityIdControl": "Windows Vista",
    "EventEnabled": "Windows Vista",

    # Shell (Vista)
    "SHGetKnownFolderPath": "Windows Vista",
    "SHSetKnownFolderPath": "Windows Vista",
    "SHGetKnownFolderIDList": "Windows Vista",
    "SHCreateItemFromParsingName": "Windows Vista",
    "SHCreateItemWithParent": "Windows Vista",
    "SHGetPropertyStoreForWindow": "Windows 7",

    # Winsock (Vista)
    "inet_ntop": "Windows Vista",
    "inet_pton": "Windows Vista",
    "GetAddrInfoExW": "Windows Vista",
    "GetAddrInfoExA": "Windows Vista",
    "FreeAddrInfoExW": "Windows Vista",
    "FreeAddrInfoExA": "Windows Vista",
    "WSAPoll": "Windows Vista",

    # User32 (Vista / 7)
    "ChangeWindowMessageFilter": "Windows Vista",
    "ChangeWindowMessageFilterEx": "Windows 7",
    "GetDisplayConfigBufferSizes": "Windows 7",
    "QueryDisplayConfig": "Windows 7",
    "SetProcessDPIAware": "Windows Vista",
    "SetProcessDpiAwarenessInternal": "Windows 8.1",

    # Threading (Vista)
    "SetThreadErrorMode": "Windows 7",
    "GetThreadErrorMode": "Windows 7",
}


def parse_imports(binary_path):
    # Try using objdump or llvm-objdump
    objdump = shutil.which("i686-w64-mingw32-objdump") or shutil.which("objdump") or shutil.which("llvm-objdump")
    if not objdump:
        print("Error: 'objdump' or 'i686-w64-mingw32-objdump' not found in PATH.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([objdump, "-p", binary_path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running objdump: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    lines = result.stdout.splitlines()
    imports = {}
    current_dll = None

    dll_pattern = re.compile(r"DLL Name:\s*(\S+)", re.IGNORECASE)
    # objdump symbol lines: "       1e3886a  1591  RegDeleteTreeW" or "     [   0] RegDeleteTreeW"
    sym_pattern = re.compile(r"^\s+(?:[0-9a-fA-F]+|\d+)\s+(?:[0-9a-fA-F]+|\d+)\s+(\S+)")
    alt_sym_pattern = re.compile(r"^\s+\[\s*\d+\]\s+(\S+)")

    in_import_section = False
    for line in lines:
        if "The Import Tables" in line or "import directory" in line.lower():
            in_import_section = True
            continue

        if not in_import_section:
            continue

        dll_match = dll_pattern.search(line)
        if dll_match:
            current_dll = dll_match.group(1).upper()
            imports[current_dll] = []
            continue

        if current_dll:
            sym_match = sym_pattern.match(line) or alt_sym_pattern.match(line)
            if sym_match:
                imports[current_dll].append(sym_match.group(1))

    return imports


def check_binary(binary_path):
    print(f"==================================================")
    print(f" Scanning: {binary_path}")
    print(f"==================================================")
    imports = parse_imports(binary_path)

    if not imports:
        print("No dynamic imports found in binary.")
        return

    incompatible_found = []

    print("\n--- Imported DLLs ---")
    for dll, symbols in sorted(imports.items()):
        dll_lower = dll.lower()
        print(f"  {dll:25} ({len(symbols)} imported functions)")

        # Check incompatible DLLs
        for bad_dll, os_req in INCOMPATIBLE_DLLS.items():
            if bad_dll.endswith("-") and dll_lower.startswith(bad_dll):
                incompatible_found.append((dll, None, os_req))
            elif dll_lower == bad_dll and "OK" not in os_req:
                incompatible_found.append((dll, None, os_req))

        # Check incompatible APIs
        for sym in symbols:
            # strip leading/trailing whitespace
            clean_sym = sym.strip()
            # on 32-bit x86 some tools show @number, strip for lookup
            base_sym = re.sub(r"@\d+$", "", clean_sym)
            if base_sym in VISTA_PLUS_APIS:
                incompatible_found.append((dll, clean_sym, VISTA_PLUS_APIS[base_sym]))

    print("\n--------------------------------------------------")
    if incompatible_found:
        print(f"[FAIL] Found {len(incompatible_found)} Vista+ incompatibilities:")
        for dll, sym, os_req in incompatible_found:
            if sym:
                print(f"   * {dll} -> {sym} (Requires: {os_req})")
            else:
                print(f"   * {dll} (Entire DLL Requires: {os_req})")
        print("\nThese APIs will prevent launching on Windows XP (NT 5.1).")
        sys.exit(1)
    else:
        print("[PASS] All imported DLLs and functions are compatible with Windows XP!")
        print("--------------------------------------------------")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_xp_compat.py <path_to_binary.exe_or_dll>")
        sys.exit(1)

    check_binary(sys.argv[1])
