# pyto-pkg

Python command line utility that installs wheels into Swift packages. Scripts are shared accross platforms (even when installed from wheels), but extensions are installed in os specific Apple Frameworks only if a supported wheel is found. The installed platforms are written in `*.dist-info/platforms.txt`.

This does not provide a cross compilation environment and is only meant to be used to install wheels and pure Python packages.

Also, this is made to work with [`pyto-runtime`](https://git.gatit.es/pyto/pyto-runtime) so tagging works differently than the official iOS wheels.

Supported platforms are: `ios`, `ios-simulator`, `ios-macabi`, `tvos`, `tvos-simulator`, `watchos` and `watchos-simulator`. Wheels must not contain the minimum os version or the llvm platform name. Example of valid wheel name: `numpy-2.3.0-cp314-cp314-ios_arm64.whl`.

## Usage

```
$ pip install git+https://git.gatit.es/pyto/pyto-pkg.git@1.0
$ pyto-pkg --output SwiftPackagePath install numpy
```

The python version used to run `pyto-pkg` will be the version running `pip`. You can configure multiple Python versions with different packages in a single Swift Package. 

You can pass a requirements file with `-r`. By default, `pyto-pkg` installs wheels for all supported platforms, but you can specify them with the `-t` argument, or you can customize them by package by adding a coma after the package name or version. Then you can write the platforms name, followed by an underscore and the architecture separated by a coma. If you want to just exclude a platform, put an exclamation mark before the platform name. For example:

```
opencv-contrib-python==4.13.0+d87edc6,!watchos_armv7k
torch==2.8.0a0+gitde3aca3,ios_arm64,ios-macabi_arm64,ios-macabi_x86_64
```

Pass `--help` for more options. By default, wheels will be pulled from `https://git.gatit.es/api/packages/pyto/pypi/simple` but you can change it with `--index-url`. Wheels are preferred over tar balls and pip will fallback to the default index repository if no wheels or packages are found in the specified repo index. You can also skip scripts with `--no-scripts` so you can `pip install` the wheels at runtime while keeping the extensions. However you need to be sure that the version of the package installed at runtime matches the version of the extensions stored in the app bundle.
