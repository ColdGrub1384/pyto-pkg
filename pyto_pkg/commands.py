from .environment import call_pip, SUPPORTED_TARGETS, DEFAULT_INDEX, OutputPackage
import os
import glob


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
        for t in includes:
            if "_" in t:
                result_targets.append(t)
            elif t in SUPPORTED_TARGETS:
                for arch in SUPPORTED_TARGETS[t]:
                    result_targets.append(f"{t}_{arch}")
            else:
                result_targets.append(t)
    else:
        # If only excludes are specified, use all except excluded ones
        for target in default_targets:
            is_excluded = False
            for ex in excludes:
                if target == ex or target.startswith(ex + "_"):
                    is_excluded = True
                    break
            if not is_excluded:
                result_targets.append(target)
    
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
    platforms_memory = {}
    for pkg_spec, pkg_targets in all_package_specs:
        for full_target in pkg_targets:
            if "_" in full_target:
                target, arch = full_target.split("_", 1)

            # 1. Read existing platforms.txt files into memory if not already there
            if os.path.exists(package.site_path):
                for dist_info in glob.glob(os.path.join(package.site_path, "*.dist-info")):
                    name = os.path.basename(dist_info)
                    platforms_file = os.path.join(dist_info, "platforms.txt")
                    if name not in platforms_memory:
                        if os.path.exists(platforms_file):
                            with open(platforms_file, "r") as f:
                                platforms_memory[name] = set(f.read().splitlines())
                        else:
                            platforms_memory[name] = set()

            args = ["install", "--use-pep517", "--prefer-binary", "--force-reinstall", "--pre", pkg_spec]
            if no_deps:
                args.append("--no-deps")
            args += ["--index-url", index_url]
            args += ["--extra-index-url", "https://pypi.org/simple"]
            call_pip(args, target, arch, package, include)

            # 2. Update platforms.txt in each dist-info
            platform_name = f"{target}_{arch}"
            if os.path.exists(package.site_path):
                for dist_info in glob.glob(os.path.join(package.site_path, "*.dist-info")):
                    name = os.path.basename(dist_info)
                    if name not in platforms_memory:
                        platforms_file = os.path.join(dist_info, "platforms.txt")
                        if os.path.exists(platforms_file):
                            with open(platforms_file, "r") as f:
                                platforms_memory[name] = set(f.read().splitlines())
                        else:
                            platforms_memory[name] = set()
                    
                    platforms_memory[name].add(platform_name)
                    
                    platforms_file = os.path.join(dist_info, "platforms.txt")
                    with open(platforms_file, "w") as f:
                        f.write("\n".join(sorted(list(platforms_memory[name]))) + "\n")

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
