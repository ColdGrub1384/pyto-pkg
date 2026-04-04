// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "PythonExtensions",
    products: [
        .library(
            name: "TargetName",
            targets: ["TargetName"]),
    ],

    targets: [
        .target(
            name: "TargetName",
            dependencies: [
                .target(name: "")
            ],
            resources: [
                // PYTHON_BUNDLES_PLACEHOLDER
            ]),

        .binaryTarget(name: "", path: "")
    ]
)
