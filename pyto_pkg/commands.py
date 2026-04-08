from .environment import call_pip, SUPPORTED_TARGETS, DEFAULT_INDEX, OutputPackage
import os


def parse_package_customization(package_spec: str, default_targets: list[str]) -> tuple[str, list[str]]:
    if "," not in package_spec:
        return package_spec, default_targets
    
    parts = package_spec.split(",")
    package_name = parts[0]
    custom_platforms = parts[1:]
    
    if not custom_platforms:
        return package_name, default_targets
    
    # Separate includes and excludes
    includes = []
    excludes = []
    
    for platform_spec in custom_platforms:
        if platform_spec.startswith("!"):
            excludes.append(platform_spec[1:])
        else:
            includes.append(platform_spec)
    
    # Build final target list
    result_targets = []
    
    if includes:
        # If includes are specified, only use those
        result_targets = includes
    else:
        # If only excludes are specified, use all except excluded ones
        result_targets = [target for target in default_targets if target not in excludes]
    
    return package_name, result_targets


def install(output: str, output_target_name: str, packages: list[str] = [], requirement: str = None, no_scripts: bool = False, no_deps: bool = False, index_url: str = DEFAULT_INDEX, targets: list[str] = [], include: list[str] = []):
    package = OutputPackage(output, output_target_name)
    
    # Build list of all packages with their customizations
    all_package_specs = []
    
    # Parse command-line packages
    for pkg_spec in packages:
        pkg_name, pkg_targets = parse_package_customization(pkg_spec, list(targets))
        all_package_specs.append((pkg_name, pkg_targets))
    
    # Parse requirement file packages
    if requirement is not None:
        with open(requirement, "r") as f:
            for line in f.readlines():
                line = line.strip().replace("\n", "")
                if line and not line.startswith("#"):
                    pkg_name, pkg_targets = parse_package_customization(line, list(targets))
                    all_package_specs.append((pkg_name, pkg_targets))
    
    # Install each package for its specified targets
    for pkg_spec, pkg_targets in all_package_specs:
        for target in pkg_targets:
            for arch in SUPPORTED_TARGETS[target]:
                args = ["install", "--use-pep517", "--prefer-binary", "--force-reinstall", "--pre", "--no-cache-dir", pkg_spec]
                if no_deps:
                    args.append("--no-deps")
                args += ["--index-url", index_url]
                args += ["--extra-index-url", "https://pypi.org/simple"]
                call_pip(args, target, arch, package, include)
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
