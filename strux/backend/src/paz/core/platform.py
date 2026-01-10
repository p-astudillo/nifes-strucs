"""
Platform detection and compatibility utilities for PAZ.

Supports:
- macOS (Intel and Apple Silicon/ARM)
- Windows (x64)
- Linux (x64)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

from paz.core.logging_config import get_logger


logger = get_logger("platform")


class OperatingSystem(str, Enum):
    """Supported operating systems."""

    MACOS = "macOS"
    WINDOWS = "Windows"
    LINUX = "Linux"
    UNKNOWN = "Unknown"


class Architecture(str, Enum):
    """CPU architectures."""

    ARM64 = "arm64"  # Apple Silicon, ARM
    X86_64 = "x86_64"  # Intel/AMD 64-bit
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlatformInfo:
    """
    Information about the current platform.

    Attributes:
        os: Operating system
        arch: CPU architecture
        os_version: OS version string
        python_version: Python version string
        is_apple_silicon: True if running on Apple Silicon
        is_macos: True if running on macOS
    """

    os: OperatingSystem
    arch: Architecture
    os_version: str
    python_version: str

    @property
    def is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon (M1/M2/M3/etc)."""
        return self.os == OperatingSystem.MACOS and self.arch == Architecture.ARM64

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self.os == OperatingSystem.MACOS

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self.os == OperatingSystem.WINDOWS

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self.os == OperatingSystem.LINUX


def get_platform_info() -> PlatformInfo:
    """
    Detect current platform information.

    Returns:
        PlatformInfo with OS, architecture, and version details
    """
    # Detect OS
    system = platform.system().lower()
    if system == "darwin":
        os_type = OperatingSystem.MACOS
    elif system == "windows":
        os_type = OperatingSystem.WINDOWS
    elif system == "linux":
        os_type = OperatingSystem.LINUX
    else:
        os_type = OperatingSystem.UNKNOWN

    # Detect architecture
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        arch = Architecture.ARM64
    elif machine in ("x86_64", "amd64"):
        arch = Architecture.X86_64
    else:
        arch = Architecture.UNKNOWN

    return PlatformInfo(
        os=os_type,
        arch=arch,
        os_version=platform.version(),
        python_version=platform.python_version(),
    )


# Cached platform info
_PLATFORM_INFO: PlatformInfo | None = None


def get_cached_platform_info() -> PlatformInfo:
    """Get cached platform information."""
    global _PLATFORM_INFO
    if _PLATFORM_INFO is None:
        _PLATFORM_INFO = get_platform_info()
    return _PLATFORM_INFO


@dataclass
class DependencyStatus:
    """Status of a dependency check."""

    name: str
    available: bool
    version: str | None = None
    path: str | None = None
    error: str | None = None


def check_opensees() -> DependencyStatus:
    """
    Check if OpenSees is available.

    Returns:
        DependencyStatus with availability and version info
    """
    # Check environment variable first
    exe = os.environ.get("OPENSEES_EXE")
    if exe:
        path = Path(exe)
        if path.exists() or shutil.which(exe):
            return DependencyStatus(
                name="OpenSees",
                available=True,
                path=str(path if path.exists() else shutil.which(exe)),
            )

    # Check PATH
    opensees_path = shutil.which("OpenSees")
    if opensees_path:
        return DependencyStatus(
            name="OpenSees",
            available=True,
            path=opensees_path,
        )

    # Check common locations
    platform_info = get_cached_platform_info()

    if platform_info.is_macos:
        common_paths = [
            "/opt/homebrew/bin/OpenSees",  # Homebrew on Apple Silicon
            "/usr/local/bin/OpenSees",  # Homebrew on Intel
            Path.home() / "OpenSees" / "bin" / "OpenSees",
        ]
    elif platform_info.is_windows:
        common_paths = [
            Path("C:/Program Files/OpenSees/bin/OpenSees.exe"),
            Path("C:/OpenSees/bin/OpenSees.exe"),
            Path.home() / "OpenSees" / "bin" / "OpenSees.exe",
        ]
    else:  # Linux
        common_paths = [
            Path("/usr/local/bin/OpenSees"),
            Path("/opt/opensees/bin/OpenSees"),
            Path.home() / "OpenSees" / "bin" / "OpenSees",
        ]

    for path in common_paths:
        if Path(path).exists():
            return DependencyStatus(
                name="OpenSees",
                available=True,
                path=str(path),
            )

    return DependencyStatus(
        name="OpenSees",
        available=False,
        error="OpenSees executable not found. Set OPENSEES_EXE or add to PATH.",
    )


def check_qt() -> DependencyStatus:
    """
    Check if Qt (PySide6) is available.

    Returns:
        DependencyStatus with availability info
    """
    try:
        from PySide6 import QtCore

        version = QtCore.qVersion()
        return DependencyStatus(
            name="Qt/PySide6",
            available=True,
            version=version,
        )
    except ImportError as e:
        return DependencyStatus(
            name="Qt/PySide6",
            available=False,
            error=str(e),
        )


def check_pyvista() -> DependencyStatus:
    """
    Check if PyVista is available.

    Returns:
        DependencyStatus with availability info
    """
    try:
        import pyvista

        return DependencyStatus(
            name="PyVista",
            available=True,
            version=pyvista.__version__,
        )
    except ImportError as e:
        return DependencyStatus(
            name="PyVista",
            available=False,
            error=str(e),
        )


def check_numpy() -> DependencyStatus:
    """
    Check if NumPy is available.

    Returns:
        DependencyStatus with availability info
    """
    try:
        import numpy

        return DependencyStatus(
            name="NumPy",
            available=True,
            version=numpy.__version__,
        )
    except ImportError as e:
        return DependencyStatus(
            name="NumPy",
            available=False,
            error=str(e),
        )


@dataclass
class CompatibilityReport:
    """
    Full compatibility report for the current system.

    Attributes:
        platform: Platform information
        dependencies: List of dependency statuses
        is_fully_compatible: True if all dependencies are available
        warnings: List of warning messages
    """

    platform: PlatformInfo
    dependencies: list[DependencyStatus]
    warnings: list[str]

    @property
    def is_fully_compatible(self) -> bool:
        """Check if all dependencies are available."""
        return all(d.available for d in self.dependencies)

    @property
    def missing_dependencies(self) -> list[DependencyStatus]:
        """Get list of missing dependencies."""
        return [d for d in self.dependencies if not d.available]


def run_compatibility_check() -> CompatibilityReport:
    """
    Run a full compatibility check.

    Returns:
        CompatibilityReport with platform info and dependency statuses
    """
    platform_info = get_cached_platform_info()
    warnings: list[str] = []

    # Check dependencies
    dependencies = [
        check_numpy(),
        check_pyvista(),
        check_qt(),
        check_opensees(),
    ]

    # Platform-specific warnings
    if platform_info.is_apple_silicon:
        logger.info("Running on Apple Silicon - using native ARM binaries")

    if platform_info.os == OperatingSystem.UNKNOWN:
        warnings.append(f"Unknown operating system: {platform.system()}")

    if platform_info.arch == Architecture.UNKNOWN:
        warnings.append(f"Unknown architecture: {platform.machine()}")

    return CompatibilityReport(
        platform=platform_info,
        dependencies=dependencies,
        warnings=warnings,
    )


def print_compatibility_report(report: CompatibilityReport | None = None) -> None:
    """
    Print a formatted compatibility report.

    Args:
        report: Compatibility report (runs check if None)
    """
    if report is None:
        report = run_compatibility_check()

    print("\n" + "=" * 60)
    print("PAZ Compatibility Report")
    print("=" * 60)

    print(f"\nPlatform: {report.platform.os.value}")
    print(f"Architecture: {report.platform.arch.value}")
    print(f"OS Version: {report.platform.os_version}")
    print(f"Python: {report.platform.python_version}")

    if report.platform.is_apple_silicon:
        print("Apple Silicon: Yes (native ARM support)")

    print("\nDependencies:")
    print("-" * 40)

    for dep in report.dependencies:
        status = "✓" if dep.available else "✗"
        version = f" ({dep.version})" if dep.version else ""
        print(f"  {status} {dep.name}{version}")
        if dep.path:
            print(f"      Path: {dep.path}")
        if dep.error:
            print(f"      Error: {dep.error}")

    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"  ⚠ {warning}")

    print("\n" + "=" * 60)

    if report.is_fully_compatible:
        print("Status: FULLY COMPATIBLE")
    else:
        missing = [d.name for d in report.missing_dependencies]
        print(f"Status: MISSING DEPENDENCIES: {', '.join(missing)}")

    print("=" * 60 + "\n")


# macOS-specific utilities

def get_macos_version() -> tuple[int, int, int] | None:
    """
    Get macOS version as tuple.

    Returns:
        (major, minor, patch) or None if not macOS
    """
    if platform.system() != "Darwin":
        return None

    try:
        version = platform.mac_ver()[0]
        parts = version.split(".")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except (ValueError, IndexError):
        return None


def is_rosetta() -> bool:
    """
    Check if running under Rosetta 2 (x86_64 emulation on ARM).

    Returns:
        True if running under Rosetta
    """
    if platform.system() != "Darwin":
        return False

    try:
        # sysctl returns 1 if running under Rosetta
        result = subprocess.run(
            ["sysctl", "-n", "sysctl.proc_translated"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "1"
    except Exception:
        return False


# Installation helpers

MACOS_INSTALL_INSTRUCTIONS: Final[str] = """
OpenSees Installation on macOS:

Option 1: Homebrew (recommended for Apple Silicon)
  brew tap opensees/opensees
  brew install opensees

Option 2: Manual installation
  1. Download OpenSees from https://opensees.berkeley.edu
  2. Extract to ~/OpenSees
  3. Add to PATH: export PATH=$PATH:$HOME/OpenSees/bin

Option 3: Set environment variable
  export OPENSEES_EXE=/path/to/OpenSees

For Apple Silicon (M1/M2/M3):
  - Use the native ARM binary for best performance
  - Avoid Rosetta emulation if possible
"""

WINDOWS_INSTALL_INSTRUCTIONS: Final[str] = """
OpenSees Installation on Windows:

1. Download OpenSees from https://opensees.berkeley.edu
2. Extract to C:\\OpenSees
3. Add to PATH: C:\\OpenSees\\bin
   Or set OPENSEES_EXE=C:\\OpenSees\\bin\\OpenSees.exe
"""

LINUX_INSTALL_INSTRUCTIONS: Final[str] = """
OpenSees Installation on Linux:

Option 1: Build from source
  See https://github.com/OpenSees/OpenSees

Option 2: Use pre-built binary
  1. Download from https://opensees.berkeley.edu
  2. Extract to /opt/opensees or ~/OpenSees
  3. Add to PATH or set OPENSEES_EXE
"""


def get_install_instructions() -> str:
    """Get installation instructions for the current platform."""
    platform_info = get_cached_platform_info()

    if platform_info.is_macos:
        return MACOS_INSTALL_INSTRUCTIONS
    elif platform_info.is_windows:
        return WINDOWS_INSTALL_INSTRUCTIONS
    else:
        return LINUX_INSTALL_INSTRUCTIONS
