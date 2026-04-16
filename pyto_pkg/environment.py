import os
import sys
import glob
import subprocess
import sysconfig
import shutil
from .frameworks import make_framework, make_xcode_frameworks


SUPPORTED_TARGETS = {
    "ios": ("arm64",), "ios-simulator": ("arm64", "x86_64"), "ios-macabi": ("arm64", "x86_64"),
    "tvos": ("arm64",), "tvos-simulator": ("arm64", "x86_64"),
    "watchos": ("arm64", "arm64_32", "armv7k"), "watchos-simulator": ("arm64", "x86_64")
}

DEFAULT_INDEX = "https://git.gatit.es/api/packages/pyto/pypi/simple"


class OutputPackage:

    def __init__(self, path: str, output_target_name: str, version: str = f"{sys.version_info.major}.{sys.version_info.minor}"):
        self.path = path
        self.version = version
        self.name = output_target_name

        short_version = version.split(".")
        if len(short_version) > 2:
            short_version = ".".join(short_version[:2])
        else:
            short_version = ".".join(short_version)

        bundle_path = os.path.join(self.path, "Sources", self.name, f"{self.name}-cp{short_version.replace(".", "")}.bundle")

        if not os.path.exists(path):
            os.makedirs(path)

        if not os.path.exists(bundle_path):
            os.makedirs(bundle_path)
        
        self.bundle_path = bundle_path
        self.site_path = os.path.join(self.bundle_path, "lib", f"python{short_version}", "site-packages")
        self.include_path = os.path.join(self.bundle_path, "include")
        self.bin_path = os.path.join(self.bundle_path, "bin")

    def package_binaries(self, platform: str, architecture: str):
        extensions = glob.glob(os.path.join(self.site_path, "**", "*.so"), recursive = True)
        libraries = glob.glob(os.path.join(self.site_path, "**", "*.dylib"), recursive = True)
        static_libraries = glob.glob(os.path.join(self.site_path, "**", "*.a"), recursive = True)

        frameworks_path = os.path.join(self.path, "Frameworks", f"{platform}.{architecture}")
        if not os.path.exists(frameworks_path):
            os.makedirs(frameworks_path)
        
        for lib in static_libraries:
            os.remove(lib)

        for ext in extensions+libraries:
            if ext.endswith(".dylib"):
                new_path = os.path.join(frameworks_path, os.path.basename(ext))
            else:
                relative_path = os.path.relpath(ext, self.site_path)
                new_name = relative_path.replace("/", "-").split(".cpython-")[0].split(".abi3")[0]+f"-cp{self.version.replace(".", "")}.dylib"
                new_path = os.path.join(frameworks_path, new_name)
            if os.path.exists(new_path):
                os.remove(new_path)
            shutil.move(ext, new_path)
        
            make_framework(new_path, platform)

    def make_xcode_frameworks(self, include_scripts: bool):
        make_xcode_frameworks(os.path.join(self.path, "Frameworks"), include_scripts, self.name)


def setup_environment(platform: str, architecture: str, output: OutputPackage, include: list[str] = []) -> dict:
    environ = os.environ.copy()

    environ["PYTHON_PLATFORM"] = platform.replace("-", "_")
    environ["PYTHON_SCRIPT_PATH"] = os.environ.get("PYTHON_SCRIPT_PATH", "")
    environ["_PYTHON_SYSCONFIGDATA_NAME"] = sysconfig._get_sysconfigdata_name()
    environ["_PYTHON_HOST_PLATFORM"] = platform+"-"+architecture
    environ["ARCHS"] = architecture

    environ["PYTHON_SITE_PATH"] = output.site_path
    environ["PYTHON_PROJ_PATH"] = output.bundle_path
    environ["PYTHON_BIN_PATH"] = output.bin_path
    environ["PYTHON_INCLUDE_PATH"] = output.include_path

    # Resolve PYTHON_ADDITIONAL_PATH to actual site-packages directories
    resolved_additional_paths = []
    if include:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        short_version = python_version.replace(".", "")

        for include_path in include:
            if not include_path:
                continue
            resolved_additional_paths.append(include_path)
            # Find the site-packages directory matching pattern: Sources/xxx/xxx-cpxxx.bundle/lib/pythonx.xx/site-packages
            pattern = os.path.join(include_path, "Sources", "*", f"*-cp{short_version}.bundle", "lib", f"python{python_version}", "site-packages")
            matching_dirs = glob.glob(pattern)
            resolved_additional_paths.extend(matching_dirs)

        if resolved_additional_paths:
            environ["PYTHON_ADDITIONAL_PATH"] = ";".join(resolved_additional_paths)

    environ["PATH"] = os.environ["PATH"]+":"+output.bin_path

    environ["PYTHON_SYSTEM"] = "Pyto"
    
    # Ensure dependencies are available during build isolation
    environ["PIP_TOOL_PATH"] = os.environ.get("PYTHON_SCRIPT_PATH", "")
    
    # Add pyto_pkg to PYTHONPATH for build backends
    pyto_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pythonpath_parts = [pyto_pkg_root]
    
    # Add resolved PYTHON_ADDITIONAL_PATH to PYTHONPATH
    if resolved_additional_paths:
        pythonpath_parts.extend(resolved_additional_paths)
    
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    
    environ["PYTHONPATH"] = ":".join(pythonpath_parts)

    match platform:
        case "ios":
            environ["SDK_NAME"] = "iphoneos"
        case "ios-simulator":
            environ["SDK_NAME"] = "iphonesimulator"
        case "ios-macabi":
            environ["SDK_NAME"] = "macosx"
        case "tvos":
            environ["SDK_NAME"] = "appletvos"
        case "tvos-simulator":
            environ["SDK_NAME"] = "appletvsimulator"
        case "watchos":
            environ["SDK_NAME"] = "watchos"
        case "watchos-simulator":
            environ["SDK_NAME"] = "watchsimulator"

    return environ

def call_pip(args: list[str], platform: str, arch: str, output: OutputPackage, include: list[str] = []) -> int:
    ret = subprocess.run([os.environ["PYTHON_SCRIPT_PATH"], "-m", "pip", "--python", os.environ["PYTHON_SCRIPT_PATH"]] + args, env=setup_environment(platform, arch, output, include))
    if ret.returncode != 0:
        print(f"Error running pip for platform '{platform}'", file=sys.stderr)
        sys.exit(ret.returncode)
