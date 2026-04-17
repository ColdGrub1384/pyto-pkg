from .commands import install, uninstall, clean
from .cross_python import main as cross_python_main
from .environment import SUPPORTED_TARGETS, DEFAULT_INDEX
import argparse
import sysconfig
import sys
import os

os.environ["PYTHON_SCRIPT_PATH"] = os.path.join(os.path.dirname(__file__), "cross_python.py")
os.putenv(f"PYTHON_SCRIPT_PATH", os.environ["PYTHON_SCRIPT_PATH"])

def main():
    parser = argparse.ArgumentParser(
        description="""Python command line utility that installs wheels into Swift packages. 
The Python version to work with is derived from the interpreter running this module and you can setup multiple Python versions in a single Swift Package.
Scripts are shared accross platforms (even when installed from wheels), but extensions are installed in os specific Apple Frameworks only if a supported wheel is found.

This does not provide a cross compilation environment and is only meant to be used to install wheels and pure Python packages.
""")
    parser.add_argument("--output", "-o", required=True, help="Path of the Swift Package directory.")
    parser.add_argument("--name", "-n", required=False, help="Specify a name for the Swift Package target name different from the package name.")
    parser.add_argument("--manifest", "-m", required=False, help="Path to a custom Package.swift template to use instead of the built-in one.")
    parser.add_argument("--include", required=False, action="append", help="Path of existing Swift Package or any directory containing Python modules that this new package depends on so dependencies are not installed twice in the same app.")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    install_parser = subparsers.add_parser("install", help="Install package(s).")
    install_parser.add_argument("packages", nargs="*", help="Package(s) to install.")
    install_parser.add_argument("--requirement", "-r", help="Read packages from a requirements file.")
    targets_choices = []
    for platform, archs in SUPPORTED_TARGETS.items():
        targets_choices.append(platform)
        for arch in archs:
            targets_choices.append(f"{platform}_{arch}")

    install_parser.add_argument("--target", "-t", required=False, help="Platforms to fetch wheels for. If none is supplied, will try to install for all supported targets.", action="append", choices=targets_choices)
    install_parser.add_argument("--no-scripts", required=False, action="store_true", help="Only install extensions so scripts can be downloaded later.")
    install_parser.add_argument("--no-deps", required=False, action="store_true", help="Skip dependencies.")
    install_parser.add_argument("--index-url", "-i", required=False, help="Primary PyPI index URL. Default value is the pyto-runtime registry and it falls back to the default PyPI index.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall package(s).")
    uninstall_parser.add_argument("packages", nargs="*", help="Package(s) to uninstall.")

    clean_parser = subparsers.add_parser("clean", help="Uninstall all packages.")

    args = parser.parse_args()
    if args.output is not None:
        args.output = os.path.abspath(args.output)
    if args.name is None:
        args.name = os.path.basename(args.output)
    if args.manifest is not None:
        args.manifest = os.path.abspath(args.manifest)
    match args.command:
        case "install":
            if not args.packages and not args.requirement:
                parser.error("At least one package or a requirements file must be specified.")
            if args.target is None:
                args.target = SUPPORTED_TARGETS.keys()
            
            expanded_targets = []
            for t in args.target:
                if "_" in t:
                    expanded_targets.append(t)
                elif t in SUPPORTED_TARGETS:
                    for arch in SUPPORTED_TARGETS[t]:
                        expanded_targets.append(f"{t}_{arch}")
            
            install(
                output=args.output,
                output_target_name=args.name,
                packages=args.packages,
                requirement=args.requirement,
                no_scripts=args.no_scripts,
                no_deps=args.no_deps,
                index_url=args.index_url or DEFAULT_INDEX,
                targets=expanded_targets,
                include=list(map(os.path.abspath, args.include)) if args.include else [],
                manifest=args.manifest
            )
        case "uninstall":
            if not args.packages:
                parser.error("At least one package must be specified to uninstall.")
            uninstall(args.output, args.packages)
        case "clean":
            clean(args.output)
        case _:
            parser.print_help()
            sys.exit(1)
    

if __name__ == "__main__":
    main()
