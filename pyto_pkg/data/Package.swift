// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "%PACKAGE_NAME%",
    products: [
        .library(
            name: "%TARGET_NAME%",
            targets: ["%TARGET_NAME%"]),
    ],

    targets: [
        .target(
            name: "%TARGET_NAME%",
            dependencies: [
                %FRAMEWORK_DEPENDENCIES%
            ],
            resources: [
%RESOURCES%
            ]),

        %FRAMEWORKS%
    ]
)
