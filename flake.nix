{
  description = "TCC IoT Benchmark — IoTDB vs InfluxDB vs TimescaleDB";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
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
      # ── dev shell ─────────────────────────────────────────────────────────
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
              python3
              gnused
              findutils
              git
            ];
            shellHook = ''
              echo "============================================="
              echo " TCC IoT Benchmark — dev shell"
              echo "============================================="
              echo "  nix run .#build             build iot-benchmark"
              echo "  nix run .#benchmark         run all benchmarks (small)"
              echo "  nix run .#benchmark --medium   medium scale"
              echo "  nix run .#benchmark --large    large scale"
              echo "  nix run .#benchmark --db iotdb --test write"
              echo "============================================="
            '';
          };
        }
      );

      # ── apps ──────────────────────────────────────────────────────────────
      apps = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};

          pythonEnv = pkgs.python3.withPackages (ps: with ps; [ ]);

          buildApp = pkgs.writeShellApplication {
            name = "build-benchmark";
            runtimeInputs = [
              pkgs.jdk17
              pkgs.maven
              pkgs.git
              pkgs.findutils
              pkgs.gnused
            ];
            text = ''
              ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
              cd "$ROOT/iot-benchmark"

              echo "[+] Building iot-benchmark modules (iotdb-1.3, influxdb-2.0, timescaledb)..."
              mvn -pl influxdb-2.0,timescaledb,iotdb-1.3 -am package -DskipTests -U

              echo "[+] Patching shebangs for NixOS / non-FHS compatibility..."
              find . -path "*/target/*" -name "*.sh" \
                -exec sed -i 's|#!/bin/bash\b|#!/usr/bin/env bash|g' {} +

              echo "[+] Build complete."
            '';
          };

          benchmarkApp = pkgs.writeShellApplication {
            name = "run-benchmark";
            runtimeInputs = [
              pkgs.jdk17
              pkgs.docker
              pkgs.docker-compose
              pythonEnv
              pkgs.git
            ];
            text = ''
              ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
              cd "$ROOT"
              exec python3 benchmark.py "$@"
            '';
          };
        in
        {
          build = {
            type = "app";
            program = "${buildApp}/bin/build-benchmark";
          };
          benchmark = {
            type = "app";
            program = "${benchmarkApp}/bin/run-benchmark";
          };
          default = {
            type = "app";
            program = "${benchmarkApp}/bin/run-benchmark";
          };
        }
      );
    };
}
