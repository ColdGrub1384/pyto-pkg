import os
import shutil
import subprocess
import re
from collections import defaultdict


INFO_PATH = os.path.join(os.path.dirname(__file__), "data", "Info.plist")
PACKAGE_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "Package.swift")


def make_framework(library_path: str, platform: str) -> None:
    framework_name = os.path.splitext(os.path.basename(library_path))[0]
    framework_path = os.path.join(os.path.dirname(library_path), f"{framework_name}.framework")

    if os.path.exists(framework_path):
        shutil.rmtree(framework_path)
    os.makedirs(framework_path)

    if platform == "ios-macabi":
        new_info_path = os.path.join(framework_path, "Versions", "A", "Resources", "Info.plist")
        new_library_path = os.path.join(framework_path, "Versions", "A", f"{framework_name}")
        if not os.path.exists(os.path.dirname(new_info_path)):
            os.makedirs(os.path.dirname(new_info_path))
    else:
        new_info_path = os.path.join(framework_path, "Info.plist")
        new_library_path = os.path.join(framework_path, f"{framework_name}")
    
    subprocess.run(["install_name_tool", "-id", f"@rpath/{framework_name}.framework/{framework_name}", library_path])
    
    # Change dependencies
    otool_output = subprocess.check_output(["otool", "-l", library_path], text=True)
    dependencies = re.findall(r"name (@rpath/.*?\.dylib) \(offset \d+\)", otool_output)
    for dep in dependencies:
        dep_name = os.path.splitext(os.path.basename(dep))[0]
        new_dep = f"@rpath/{dep_name}.framework/{dep_name}"
        subprocess.run(["install_name_tool", "-change", dep, new_dep, library_path])

    shutil.move(library_path, new_library_path)

    match platform:
        case "ios":
            minimum_os_version = "13.0"
            info_platform = "iPhoneOS"
        case "ios-simulator":
            minimum_os_version = "13.0"
            info_platform = "iPhoneSimulator"
        case "ios-macabi":
            minimum_os_version = "11.0"
            info_platform = "MacOSX"
        case "watchos":
            minimum_os_version = "6.0"
            info_platform = "WatchOS"
        case "watchos-simulator":
            minimum_os_version = "6.0"
            info_platform = "WatchSimulator"
        case "tvos":
            minimum_os_version = "13.0"
            info_platform = "AppleTVOS"
        case "tvos-simulator":
            minimum_os_version = "13.0"
            info_platform = "AppleTVSimulator"
        case _:
            raise ValueError(f"Unsupported platform: {platform}")

    with open(INFO_PATH, "r") as info_file:
        info_content = info_file.read()
        info_content = info_content.replace("%NAME%", framework_name)
        info_content = info_content.replace("%BUNDLE_ID%", f"com.pyto.{framework_name.replace("-", "").replace("_", "")}")
        info_content = info_content.replace("%PLATFORM%", info_platform)
        info_content = info_content.replace("%MINIMUM_OS_VERSION%", minimum_os_version)
        with open(new_info_path, "w") as new_info_file:
            new_info_file.write(info_content)
    
    if platform == "ios-macabi":
        cwd = os.getcwd()
        os.chdir(os.path.join(framework_path, "Versions"))
        os.symlink("A", "Current")
        os.chdir(framework_path)
        os.symlink("Versions/Current/Resources", "Resources")
        os.symlink(os.path.join("Versions/Current", framework_name), framework_name)
        os.chdir(cwd)


def make_xcode_frameworks(frameworks_path: str, include_scripts: bool, target_name: str):
    output_path = os.path.abspath(os.path.join(frameworks_path, ".."))

    frameworks = {}
    for platform in os.listdir(frameworks_path):
        if platform.split(".")[1] == "universal":
            continue
        platform_name = platform.split(".")[0]
        if platform_name not in frameworks:
            frameworks[platform_name] = []
        try:
            for framework in os.listdir(os.path.join(frameworks_path, platform)):
                frameworks[platform_name].append(os.path.join(frameworks_path, platform, framework))
        except NotADirectoryError:
            continue

    grouped_by_arch = {}
    for platform, paths in frameworks.items():
        files_by_basename = defaultdict(list)

        for path in paths:
            basename = os.path.basename(path)
            files_by_basename[basename].append(path)

        grouped_by_arch[platform] = [tuple(paths) for paths in files_by_basename.values()]

    merged_frameworks = {}
    for platform, frameworks in grouped_by_arch.items():
        universal_path = os.path.join(frameworks_path, f"{platform}.universal")
        platform_merged_frameworks = []
        for frameworks_to_merge in frameworks:
            if len(frameworks_to_merge) == 1:
                platform_merged_frameworks.append(frameworks_to_merge[0])
            else:
                if not os.path.exists(universal_path):
                    os.makedirs(universal_path)
                
                binary_name = os.path.basename(os.path.splitext(frameworks_to_merge[0])[0])
                output_binary = os.path.join(universal_path, binary_name)
                command = ["lipo", "-create"]+list(map(lambda x: os.path.join(x, binary_name), frameworks_to_merge))+["-output", output_binary]
                ret = subprocess.run(command)
                if ret.returncode != 0:
                    msg = f"Error merging {frameworks_to_merge}."
                    raise RuntimeError(msg)

                output_framework = os.path.join(universal_path, os.path.basename(frameworks_to_merge[0]))
                if os.path.exists(output_framework):
                    shutil.rmtree(output_framework)

                shutil.copytree(frameworks_to_merge[0], output_framework, symlinks=True)
                if platform == "ios-macabi":
                    framework_binary = os.path.join(output_framework, "Versions/A", binary_name)
                else:
                    framework_binary = os.path.join(output_framework, binary_name)

                os.remove(framework_binary)
                shutil.move(output_binary, framework_binary)
                platform_merged_frameworks.append(output_framework)

        merged_frameworks[platform] = platform_merged_frameworks
    
    registered_frameworks = defaultdict(list)
    for platform, frameworks in merged_frameworks.items():
        for framework in frameworks:
            basename = os.path.basename(framework)
            registered_frameworks[basename].append(framework)

    output_xcode_frameworks = []
    for basename, paths in registered_frameworks.items():
        output_xcode_framework = os.path.join(output_path, os.path.splitext(basename)[0]+".xcframework")
        if os.path.exists(output_xcode_framework):
            shutil.rmtree(output_xcode_framework)
        command = ["xcodebuild", "-create-xcframework"]
        for path in paths:
            command += ["-framework", path]
        command += ["-output", output_xcode_framework]
        ret = subprocess.run(command)
        if ret.returncode != 0:
            msg = f"Error merging {paths}."
            raise RuntimeError(msg)
        output_xcode_frameworks.append(output_xcode_framework)

    frameworks_declaration = ""
    targets_declaration = ""
    for framework in output_xcode_frameworks:
        name = os.path.basename(os.path.splitext(framework)[0])
        targets_declaration += f'                .target(name: "{name}"),\n'
        frameworks_declaration += f'        .binaryTarget(name: "{name}", path: "{os.path.basename(framework)}"),\n'

    # Discover all Python version bundles
    sources_path = os.path.join(output_path, "Sources", target_name)
    bundles_declaration = ""
    if os.path.exists(sources_path):
        bundles = sorted([d for d in os.listdir(sources_path) if d.endswith(".bundle") and d.startswith(target_name + "-cp")])
        for bundle in bundles:
            bundles_declaration += f'                .copy("{bundle}"),\n'

    new_package_manifest_path = os.path.join(output_path, "Package.swift")
    with open(PACKAGE_MANIFEST_PATH, "r") as package_manifest:
        content = package_manifest.read()
        content = content.replace('                .target(name: "")', targets_declaration)
        content = content.replace('        .binaryTarget(name: "", path: "")', frameworks_declaration)
        content = content.replace("// PYTHON_BUNDLES_PLACEHOLDER", bundles_declaration.rstrip('\n'))
        content = content.replace("PythonExtensions", os.path.basename(output_path))
        content = content.replace("TargetName", target_name)
        if not include_scripts:
            content = content.replace(".copy", "// .copy")

        with open(new_package_manifest_path, "w+") as new_package_manifest:
            new_package_manifest.write(content)

    with open(os.path.join(output_path, "Sources", target_name, os.path.basename(output_path)+".swift"), "w+") as f:
        f.write("// empty\n")

    shutil.rmtree(frameworks_path)
