// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "PythonExtensions",
    products: [
        .library(
            name: "PythonExtensions",
            targets: ["PythonExtensions"]),
    ],

    targets: [
        .target(
            name: "PythonExtensions",
            dependencies: [
                .target(name: "")
            ],
            resources: [
                .copy("PythonExtensions-cp314.bundle"),
            ]),

        .binaryTarget(name: "", path: "")
    ]
)
