{
  description = "Beangulp SimpleFIN importer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        pythonPackages = python.pkgs;

        beangulp-simplefin = pythonPackages.buildPythonPackage {
          pname = "beangulp-simplefin";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          nativeBuildInputs = [ pythonPackages.setuptools ];

          propagatedBuildInputs = [
            pythonPackages.beancount
            pythonPackages.beangulp
          ];

          nativeCheckInputs = [ pythonPackages.pytest ];

          pythonImportsCheck = [ "beangulp_simplefin" ];
        };

        devPython = python.withPackages (ps: [
          ps.beancount
          ps.beangulp
          ps.pytest
          ps.mypy
          beangulp-simplefin
        ]);
      in
      {
        packages.default = beangulp-simplefin;

        devShells.default = pkgs.mkShell {
          buildInputs = [
            devPython
            pkgs.ruff
            pkgs.pre-commit
            pkgs.uv
          ];

          shellHook = ''
            echo "beangulp-simplefin dev environment"
            echo "Python: $(python --version)"
            echo ""
            echo "Commands:"
            echo "  pre-commit run --all-files  - Run all checks"
            echo "  pytest tests/ -v            - Run tests"
          '';
        };
      }
    );
}
