//! Kubernetes CRDs for system-upgrade-controller
//!
//! This library provides automatically generated types for the [system-upgrade-controller] CRDs. It is
//! intended to be used with the [Kube-rs] library.
//!
//! [system-upgrade-controller]: https://github.com/rancher/system-upgrade-controller
//! [Kube-rs]: https://kube.rs/

pub mod plans;
pub use plans::*;
