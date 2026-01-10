"""Tests for platform compatibility module."""

import platform
from unittest.mock import patch

import pytest

from paz.core.platform import (
    Architecture,
    CompatibilityReport,
    DependencyStatus,
    OperatingSystem,
    PlatformInfo,
    check_numpy,
    check_opensees,
    check_pyvista,
    check_qt,
    get_install_instructions,
    get_macos_version,
    get_platform_info,
    run_compatibility_check,
)


class TestPlatformInfo:
    """Tests for PlatformInfo class."""

    def test_apple_silicon_detection(self) -> None:
        """Apple Silicon is correctly identified."""
        info = PlatformInfo(
            os=OperatingSystem.MACOS,
            arch=Architecture.ARM64,
            os_version="14.0",
            python_version="3.12.0",
        )
        assert info.is_apple_silicon is True
        assert info.is_macos is True

    def test_intel_mac_not_apple_silicon(self) -> None:
        """Intel Mac is not Apple Silicon."""
        info = PlatformInfo(
            os=OperatingSystem.MACOS,
            arch=Architecture.X86_64,
            os_version="14.0",
            python_version="3.12.0",
        )
        assert info.is_apple_silicon is False
        assert info.is_macos is True

    def test_windows_detection(self) -> None:
        """Windows is correctly identified."""
        info = PlatformInfo(
            os=OperatingSystem.WINDOWS,
            arch=Architecture.X86_64,
            os_version="10.0.19041",
            python_version="3.12.0",
        )
        assert info.is_windows is True
        assert info.is_macos is False
        assert info.is_apple_silicon is False

    def test_linux_detection(self) -> None:
        """Linux is correctly identified."""
        info = PlatformInfo(
            os=OperatingSystem.LINUX,
            arch=Architecture.X86_64,
            os_version="5.15.0",
            python_version="3.12.0",
        )
        assert info.is_linux is True
        assert info.is_macos is False


class TestGetPlatformInfo:
    """Tests for get_platform_info function."""

    def test_returns_platform_info(self) -> None:
        """get_platform_info returns valid PlatformInfo."""
        info = get_platform_info()

        assert isinstance(info, PlatformInfo)
        assert info.os in OperatingSystem
        assert info.arch in Architecture
        assert len(info.python_version) > 0

    def test_current_platform(self) -> None:
        """Platform info matches current system."""
        info = get_platform_info()

        if platform.system() == "Darwin":
            assert info.os == OperatingSystem.MACOS
        elif platform.system() == "Windows":
            assert info.os == OperatingSystem.WINDOWS
        elif platform.system() == "Linux":
            assert info.os == OperatingSystem.LINUX


class TestDependencyChecks:
    """Tests for dependency check functions."""

    def test_check_numpy_available(self) -> None:
        """NumPy should be available in test environment."""
        status = check_numpy()

        assert status.name == "NumPy"
        assert status.available is True
        assert status.version is not None

    def test_check_pyvista_available(self) -> None:
        """PyVista should be available in test environment."""
        status = check_pyvista()

        assert status.name == "PyVista"
        assert status.available is True
        assert status.version is not None

    def test_check_qt_available(self) -> None:
        """Qt/PySide6 should be available in test environment."""
        status = check_qt()

        assert status.name == "Qt/PySide6"
        assert status.available is True
        assert status.version is not None

    def test_check_opensees_returns_status(self) -> None:
        """check_opensees returns a valid status."""
        status = check_opensees()

        assert status.name == "OpenSees"
        assert isinstance(status.available, bool)

        if status.available:
            assert status.path is not None
        else:
            assert status.error is not None

    def test_dependency_status_structure(self) -> None:
        """DependencyStatus has correct structure."""
        status = DependencyStatus(
            name="TestDep",
            available=True,
            version="1.0.0",
            path="/usr/bin/test",
        )

        assert status.name == "TestDep"
        assert status.available is True
        assert status.version == "1.0.0"
        assert status.path == "/usr/bin/test"
        assert status.error is None


class TestCompatibilityReport:
    """Tests for compatibility report."""

    def test_run_compatibility_check(self) -> None:
        """run_compatibility_check returns valid report."""
        report = run_compatibility_check()

        assert isinstance(report, CompatibilityReport)
        assert isinstance(report.platform, PlatformInfo)
        assert len(report.dependencies) > 0
        assert isinstance(report.warnings, list)

    def test_is_fully_compatible(self) -> None:
        """is_fully_compatible works correctly."""
        # All available
        report = CompatibilityReport(
            platform=get_platform_info(),
            dependencies=[
                DependencyStatus(name="A", available=True),
                DependencyStatus(name="B", available=True),
            ],
            warnings=[],
        )
        assert report.is_fully_compatible is True

        # One missing
        report2 = CompatibilityReport(
            platform=get_platform_info(),
            dependencies=[
                DependencyStatus(name="A", available=True),
                DependencyStatus(name="B", available=False),
            ],
            warnings=[],
        )
        assert report2.is_fully_compatible is False

    def test_missing_dependencies(self) -> None:
        """missing_dependencies returns only unavailable deps."""
        report = CompatibilityReport(
            platform=get_platform_info(),
            dependencies=[
                DependencyStatus(name="A", available=True),
                DependencyStatus(name="B", available=False),
                DependencyStatus(name="C", available=True),
                DependencyStatus(name="D", available=False),
            ],
            warnings=[],
        )

        missing = report.missing_dependencies
        assert len(missing) == 2
        assert missing[0].name == "B"
        assert missing[1].name == "D"


class TestMacOSUtils:
    """Tests for macOS-specific utilities."""

    def test_get_macos_version_on_macos(self) -> None:
        """get_macos_version returns tuple on macOS."""
        if platform.system() != "Darwin":
            pytest.skip("Not running on macOS")

        version = get_macos_version()

        assert version is not None
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)
        assert version[0] >= 10  # At least macOS 10.x

    def test_get_macos_version_not_macos(self) -> None:
        """get_macos_version returns None on non-macOS."""
        with patch("paz.core.platform.platform.system", return_value="Windows"):
            version = get_macos_version()
            assert version is None


class TestInstallInstructions:
    """Tests for installation instructions."""

    def test_get_install_instructions_not_empty(self) -> None:
        """get_install_instructions returns non-empty string."""
        instructions = get_install_instructions()

        assert isinstance(instructions, str)
        assert len(instructions) > 100  # Should have meaningful content
        assert "OpenSees" in instructions

    def test_macos_instructions(self) -> None:
        """macOS instructions mention Homebrew."""
        with patch("paz.core.platform.get_cached_platform_info") as mock:
            mock.return_value = PlatformInfo(
                os=OperatingSystem.MACOS,
                arch=Architecture.ARM64,
                os_version="14.0",
                python_version="3.12.0",
            )
            instructions = get_install_instructions()
            assert "Homebrew" in instructions or "brew" in instructions

    def test_windows_instructions(self) -> None:
        """Windows instructions mention Windows paths."""
        with patch("paz.core.platform.get_cached_platform_info") as mock:
            mock.return_value = PlatformInfo(
                os=OperatingSystem.WINDOWS,
                arch=Architecture.X86_64,
                os_version="10.0",
                python_version="3.12.0",
            )
            instructions = get_install_instructions()
            assert "Windows" in instructions or "C:\\" in instructions
