from .environment import call_pip, SUPPORTED_TARGETS, DEFAULT_INDEX, OutputPackage
import os
import glob
import shutil


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


def install(output: str, output_target_name: str, packages: list[str] = [], requirement: str = None, no_scripts: bool = False, no_deps: bool = False, index_url: str = DEFAULT_INDEX, targets: list[str] = [], include: list[str] = [], manifest: str = None):
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

    # Group packages by target
    target_groups = {}
    for pkg_name, pkg_targets in all_package_specs:
        for full_target in pkg_targets:
            if full_target not in target_groups:
                target_groups[full_target] = []
            target_groups[full_target].append(pkg_name)

    # Install for each target
    for full_target, target_packages in target_groups.items():
        if "_" in full_target:
            target, arch = full_target.split("_", 1)
        else:
            continue

        # Move current site-packages to a temporary location
        backup_path = package.site_path + ".old"
        if os.path.exists(package.site_path):
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.move(package.site_path, backup_path)

        os.makedirs(package.site_path, exist_ok=True)

        if target_packages:
            args = ["install", "--use-pep517", "--prefer-binary", "--pre"]
            if no_deps:
                args.append("--no-deps")
            args += ["--index-url", index_url, "--extra-index-url", "https://pypi.org/simple"]
            args += target_packages
            call_pip(args, target, arch, package, include)

        # Update platforms.txt in the newly installed packages
        platform_name = f"{target}_{arch}"
        for dist_info in glob.glob(os.path.join(package.site_path, "*.dist-info")):
            platforms_file = os.path.join(dist_info, "platforms.txt")
            platforms = set()
            if os.path.exists(platforms_file):
                with open(platforms_file, "r") as f:
                    platforms = set(f.read().splitlines())

            platforms.add(platform_name)
            with open(platforms_file, "w") as f:
                f.write("\n".join(sorted(list(platforms))) + "\n")

        # Merge back the backup
        if os.path.exists(backup_path):
            for item in os.listdir(backup_path):
                src = os.path.join(backup_path, item)
                dst = os.path.join(package.site_path, item)

                if item.endswith(".dist-info") and os.path.exists(dst):
                    # Merge platforms.txt
                    old_platforms_file = os.path.join(src, "platforms.txt")
                    new_platforms_file = os.path.join(dst, "platforms.txt")

                    if os.path.exists(old_platforms_file):
                        with open(old_platforms_file, "r") as f:
                            old_platforms = set(f.read().splitlines())
                        with open(new_platforms_file, "r") as f:
                            new_platforms = set(f.read().splitlines())

                        merged_platforms = old_platforms.union(new_platforms)
                        with open(new_platforms_file, "w") as f:
                            f.write("\n".join(sorted(list(merged_platforms))) + "\n")
                elif not os.path.exists(dst):
                    shutil.move(src, dst)

            shutil.rmtree(backup_path)

        package.package_binaries(target, arch)

    package.make_xcode_frameworks(not no_scripts, manifest)

    for subdir, dirs, files in os.walk(package.bundle_path):
        for file in files:
            path = os.path.join(subdir, file)
            if os.path.splitext(os.path.join(subdir, file))[-1] == ".pyc":
                os.remove(path)

def uninstall(output: str, packages: list[str]):
    print(f"Uninstalling packages: {packages}, output: {output}")


def clean(output: str):
    print(f"Cleaning packages in output: {output}")
