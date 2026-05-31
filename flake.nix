{
  description = "TCC IoT Benchmark — IoTDB vs InfluxDB vs TimescaleDB";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSystem = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      apps = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          texlive = pkgs.texlive.combined.scheme-full;

          fmtScript = pkgs.writeShellScriptBin "fmt-thesis" ''
            set -e
            root=$(${pkgs.git}/bin/git rev-parse --show-toplevel)
            latex_dir="$root/tcc2-latex"

            echo "[fmt] Formatting refs.bib with bibtex-tidy..."
            tmp=$(mktemp)
            ${pkgs.bibtex-tidy}/bin/bibtex-tidy \
              --space=2 --align=14 --sort-fields --trailing-commas --no-escape \
              < "$latex_dir/refs.bib" > "$tmp"
            mv "$tmp" "$latex_dir/refs.bib"

            echo "[fmt] Formatting .tex files with tex-fmt..."
            ${pkgs.findutils}/bin/find "$latex_dir" -name "*.tex" -print0 \
              | ${pkgs.findutils}/bin/xargs -0 \
                  ${pkgs.tex-fmt}/bin/tex-fmt --nowrap

            echo "[fmt] Done."
          '';

          script = pkgs.writeShellScriptBin "build-thesis" ''
            set -e
            origdir=$(pwd)

            build_one() {
              local lang="$1"   # en or pt
              local main="$2"   # main-en.tex or main-pt.tex
              local out="$3"    # thesis-en.pdf or thesis-pt.pdf

              echo "[thesis] Building $lang version ($main)..."
              tmpdir=$(mktemp -d)
              cp -r "$origdir/tcc2-latex/." "$tmpdir/"
              cd "$tmpdir"
              HOME=$(mktemp -d) ${texlive}/bin/latexmk -pdf -bibtex -interaction=nonstopmode "$main"
              cp "''${main%.tex}.pdf" "$origdir/$out"
              echo "[thesis] $lang PDF written to $origdir/$out"
              rm -rf "$tmpdir"
              cd "$origdir"
            }

            build_one "English"    "main-en-us.tex" "thesis-en-us.pdf"
            build_one "Portuguese" "main-pt-br.tex" "thesis-pt-br.pdf"

            echo "[thesis] Done. Outputs: thesis-en-us.pdf  thesis-pt-br.pdf"
          '';
        in
        {
          thesis = {
            type = "app";
            program = "${script}/bin/build-thesis";
          };
          fmt = {
            type = "app";
            program = "${fmtScript}/bin/fmt-thesis";
          };
        }
      );

      devShells = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              jdk17
              maven
              docker
              docker-compose
              (python3.withPackages (
                ps: with ps; [
                  matplotlib
                  numpy
                  pandas
                ]
              ))
              gnused
              findutils
              git
              bibtex-tidy
              tex-fmt
            ];
            shellHook = ''
              if [ ! -f "$PWD/iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0/iot-benchmark-influxdb-2.0/benchmark.sh" ] || \
                 [ ! -f "$PWD/iot-benchmark/timescaledb/target/iot-benchmark-timescaledb/iot-benchmark-timescaledb/benchmark.sh" ] || \
                 [ ! -f "$PWD/iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3/iot-benchmark-iotdb-1.3/benchmark.sh" ]; then
                echo "[+] Building iot-benchmark modules (first time setup)..."
                (
                  cd "$PWD/iot-benchmark"
                  mvn -pl influxdb-2.0,timescaledb,iotdb-1.3 -am package -DskipTests -U
                  find . -path "*/target/*" -name "*.sh" \
                    -exec sed -i 's|#!/bin/bash\b|#!/usr/bin/env bash|g' {} +
                )
                echo "[+] Build complete."
              else
                echo "[+] iot-benchmark already built, skipping."
              fi

              echo "======================================================================="
              echo " TCC IoT Benchmark — dev shell                                         "
              echo "======================================================================="
              echo "  python3 benchmark.py                       run all DBs, small scale  "
              echo "  python3 benchmark.py --scale medium        medium scale (~30 min)    "
              echo "  python3 benchmark.py --scale large         large scale (~2 h)        "
              echo "  python3 benchmark.py --db iotdb            iotdb only                "
              echo "  python3 benchmark.py --test write          write only                "
              echo "  python3 charts.py                          all sources, en-us        "
              echo "  python3 charts.py --source medium          single source             "
              echo "  python3 charts.py --language pt-br         portuguese labels         "
              echo "-----------------------------------------------------------------------"
              echo "  nix run .#fmt                              format files              "
              echo "  nix run .#thesis                           compile thesis            "
              echo "======================================================================="
            '';
          };
        }
      );
    };
}
