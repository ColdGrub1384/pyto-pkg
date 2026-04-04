from .commands import install, uninstall, clean
from .cross_python import main as cross_python_main
from .environment import SUPPORTED_TARGETS, DEFAULT_INDEX
import argparse
import sysconfig
import sys
import os

os.environ["PYTHON_SCRIPT_PATH"] = os.path.join(sysconfig.get_path("scripts", f"{os.name}_prefix"), "pyto-cross-python")
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
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    install_parser = subparsers.add_parser("install", help="Install package(s).")
    install_parser.add_argument("packages", nargs="*", help="Package(s) to install.")
    install_parser.add_argument("--requirement", "-r", help="Read packages from a requirements file.")
    install_parser.add_argument("--target", "-t", required=False, help="Platforms to fetch wheels for. If none is supplied, will try to install for all supported targets.", action="append", choices=SUPPORTED_TARGETS.keys())
    install_parser.add_argument("--no-scripts", required=False, action="store_true", help="Only install extensions so scripts can be downloaded later.")
    install_parser.add_argument("--no-deps", required=False, action="store_true", help="Skip dependencies.")
    install_parser.add_argument("--index-url", "-i", required=False, help="Primary PyPI index URL. Default value is the pyto-runtime registry and it falls back to the default PyPI index.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall package(s).")
    uninstall_parser.add_argument("packages", nargs="*", help="Package(s) to uninstall.")

    clean_parser = subparsers.add_parser("clean", help="Uninstall all packages.")

    parser.add_argument("--output", "-o", required=True, help="Path of the Swift Package directory.")

    args = parser.parse_args()
    if args.output is not None:
        args.output = os.path.abspath(args.output)
    if args.name is None:
        args.name = os.path.basename(args.output)
    match args.command:
        case "install":
            if not args.packages and not args.requirement:
                parser.error("At least one package or a requirements file must be specified.")
            if args.target is None:
                args.target = SUPPORTED_TARGETS.keys()
            install(
                output=args.output,
                output_target_name=args.name,
                packages=args.packages,
                requirement=args.requirement,
                no_scripts=args.no_scripts,
                no_deps=args.no_deps,
                index_url=args.index_url or DEFAULT_INDEX,
                targets=args.target
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
