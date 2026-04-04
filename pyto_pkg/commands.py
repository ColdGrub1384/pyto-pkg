from .environment import call_pip, SUPPORTED_TARGETS, DEFAULT_INDEX, OutputPackage
import os


def install(output: str, output_target_name: str, packages: list[str] = [], requirement: str = None, no_scripts: bool = False, no_deps: bool = False, index_url: str = DEFAULT_INDEX, targets: list[str] = []):
    package = OutputPackage(output, output_target_name)
    for target in targets:
        for arch in SUPPORTED_TARGETS[target]:
            args = ["install", "--prefer-binary", "--force-reinstall"] + packages
            if requirement is not None:
                with open(requirement, "r") as f:
                    for pkg in f.readlines():
                        if pkg != "":
                            args.append(pkg.strip().replace("\n", ""))
            if no_deps:
                args.append("--no-deps")
            args += ["--index-url", index_url]
            args += ["--extra-index-url", "https://pypi.org/simple"]
            call_pip(args, target, arch, package)
            package.package_binaries(target, arch)
    package.make_xcode_frameworks(not no_scripts)

    for subdir, dirs, files in os.walk(package.bundle_path):
        for file in files:
            path = os.path.join(subdir, file)
            if os.path.splitext(os.path.join(subdir, file))[-1] == ".pyc":
                os.remove(path)

def uninstall(output: str, packages: list[str]):
    print(f"Uninstalling packages: {packages}, output: {output}")


def clean(output: str):
    print(f"Cleaning packages in output: {output}")
