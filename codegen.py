#!/usr/bin/env python3

import yaml
import requests
import tempfile
import subprocess


rust_lib = """//! Kubernetes CRDs for system-upgrade-controller
//!
//! This library provides automatically generated types for the [system-upgrade-controller] CRDs. It is
//! intended to be used with the [Kube-rs] library.
//!
//! [system-upgrade-controller]: https://github.com/rancher/system-upgrade-controller
//! [Kube-rs]: https://kube.rs/

"""


crds = yaml.safe_load_all(
    requests.get(
        "https://github.com/rancher/system-upgrade-controller/releases/download/v0.13.4/crd.yaml"
    ).text
)

for crd in crds:
    if crd == None:
        continue
    file_name = crd["metadata"]["name"].removesuffix(".upgrade.cattle.io")
    if file_name == crd["metadata"]["name"]:
        continue
    rust_code = ""
    if crd["kind"] != "CustomResourceDefinition":
        continue
    # Save the CRD as a tmp yaml file
    with tempfile.NamedTemporaryFile(mode="w") as f:
        yaml.dump(crd, f)
        tmp_file = f.name
        rust_code = subprocess.run(
            [
                "kopium",
                "-f",
                tmp_file,
                "--schema=derived",
                "--docs",
                "-b",
                "--derive=Default",
                "--derive=PartialEq",
                "--smart-derive-elision",
            ],
            capture_output=True,
        )
        if rust_code.returncode != 0:
            print(rust_code.stderr.decode("utf-8"))
            exit(1)
        rust_code = rust_code.stdout.decode("utf-8")

    rust_code = rust_code.replace(
        f"// kopium command: kopium -f {tmp_file} --schema=derived --docs -b --derive=Default --derive=PartialEq --smart-derive-elision",
        f"// kopium command: kopium -f {file_name}.yml --schema=derived --docs -b --derive=Default --derive=PartialEq --smart-derive-elision",
    )
    rust_code = "\n".join(
        [
            line.replace("#[builder(", '#[cfg_attr(feature = "builder", builder(')
            .strip()
            .removesuffix("]")
            + ")]"
            if "#[builder(" in line
            else line
            for line in rust_code.split("\n")
        ]
    )
    rust_code = "\n".join(
        [
            line.replace(
                ", TypedBuilder, Default, PartialEq, JsonSchema)]",
                ', Default, PartialEq)]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\n#[cfg_attr(not(feature = "schemars"), kube(schema="disabled"))]',
            ).replace(
                ", TypedBuilder, PartialEq, JsonSchema)]",
                ', PartialEq)]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\n#[cfg_attr(not(feature = "schemars"), kube(schema="disabled"))]',
            ).replace(
                ", Default, PartialEq, JsonSchema)]",
                ', Default, PartialEq)]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\n#[cfg_attr(not(feature = "schemars"), kube(schema="disabled"))]',
            ).replace(
                ", PartialEq, JsonSchema)]",
                ', PartialEq)]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\n#[cfg_attr(not(feature = "schemars"), kube(schema="disabled"))]',
            )
            if line.startswith("#[derive(") and "CustomResource" in line
            else line.replace(
                ", TypedBuilder, Default, PartialEq, JsonSchema)]",
                ', Default, PartialEq)]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]',
            ).replace(
                ", TypedBuilder, PartialEq, JsonSchema)]",
                ', PartialEq)]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]',
            ).replace(
                ", Default, PartialEq, JsonSchema)]",
                ', Default, PartialEq)]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]',
            ).replace(
                ", PartialEq, JsonSchema)]",
                ', PartialEq)]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]',
            )
            if line.startswith("#[derive(")
            else line
            for line in rust_code.split("\n")
        ]
    )
    rust_code = (
        rust_code.replace(
            "pub use typed_builder::TypedBuilder;",
            '#[cfg(feature = "builder")]\npub use typed_builder::TypedBuilder;',
        )
        .replace(
            "pub use schemars::JsonSchema;",
            '#[cfg(feature = "schemars")]\npub use schemars::JsonSchema;',
        )
        .replace(
            "pub use kube::CustomResource;", "pub use kube_derive::CustomResource;"
        )
        .replace(
            '#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\npub enum',
            '#[cfg_attr(feature = "schemars", derive(JsonSchema))]\npub enum',
        )
    )
    rust_file = f"./src/{file_name}.rs"
    rust_lib += f"pub mod {file_name};\npub use {file_name}::*;\n"
    with open(rust_file, "w") as f:
        f.write(rust_code)
    # Format the code
    subprocess.run(["rustfmt", rust_file])

with open("./src/lib.rs", "w") as f:
    f.write(rust_lib)
