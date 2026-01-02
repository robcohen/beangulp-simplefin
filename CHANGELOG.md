# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-01-02

### Added

- Custom `cmp` method for deduplication by `simplefin_id`
  - Transactions with matching `simplefin_id` are considered duplicates
  - Transactions where only one has `simplefin_id` are never duplicates
  - Falls back to date/amount/account comparison when neither has `simplefin_id`

## [0.1.0] - 2025-01-01

### Added

- Initial release
- `SimpleFINImporter` class for importing SimpleFIN JSON data
- Support for per-account JSON format from `simplefin fetch`
- Automatic balance assertions from account data
- Configurable expense/income accounts for counter-postings
- Full type annotations with `py.typed` marker
- CI workflow with tests on Python 3.9-3.13
- Pre-commit hooks for code quality

[Unreleased]: https://github.com/robcohen/beangulp-simplefin/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/robcohen/beangulp-simplefin/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/robcohen/beangulp-simplefin/releases/tag/v0.1.0
