{
  description = "Reproducible Benchmark Environment with Git Submodules";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSystem = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      devShells = forEachSystem (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              go
              gnumake
              jdk17
              maven
              docker
              docker-compose
              gnused
              findutils
            ];

            shellHook = ''
              export ROOT_DIR=$PWD

              echo "======================================================="
              echo " Initializing Benchmark Environment..."
              echo "======================================================="

              # 1. Start the Databases
              if [ -f "docker-compose.yml" ]; then
                echo "[+] Starting databases via docker compose..."
                docker-compose up -d
              else
                echo "[-] Warning: docker-compose.yml not found."
              fi

              # 2. Compile TSBS Submodule
              if [ -d "questdb-tsbs" ]; then
                if [ ! -f "questdb-tsbs/.nix-built" ]; then
                  echo "[+] Compiling QuestDB TSBS submodule..."
                  cd questdb-tsbs
                  make all
                  touch .nix-built
                  cd $ROOT_DIR
                else
                  echo "[+] TSBS submodule is already compiled."
                fi
                export PATH=$ROOT_DIR/questdb-tsbs/bin:$PATH
              else
                echo "[-] Warning: questdb-tsbs submodule missing. Run: git submodule update --init"
              fi

              # 3. Compile IoT-Benchmark Submodule
              if [ -d "iot-benchmark" ]; then
                if [ ! -f "iot-benchmark/.nix-built" ]; then
                  echo "[+] Compiling IoT-Benchmark submodule (Targeted build)..."
                  cd iot-benchmark
                  
                  # Targeted Maven build: Only compile the databases we actually need
                  mvn clean package -pl influxdb-2.0,timescaledb,iotdb-1.3 -am -Dmaven.test.skip=true -U
                  
                  echo "[+] Patching NixOS shebangs for IoT-Benchmark scripts..."
                  IOTDB_SCRIPT=$(find . -name "benchmark.sh" | grep "iot-benchmark-iotdb" | head -n 1)
                  
                  # Safety check: Only patch and mark as built if the script actually exists
                  if [ -n "$IOTDB_SCRIPT" ]; then
                    IOTDB_DIR=$(dirname "$IOTDB_SCRIPT")
                    cd "$IOTDB_DIR"
                    sed -i 's|#!/bin/bash|#!/usr/bin/env bash|g' benchmark.sh bin/*.sh
                    
                    cd $ROOT_DIR/iot-benchmark
                    touch .nix-built
                    echo "[+] IoT-Benchmark successfully built and patched."
                  else
                    echo "[-] Build failed: Could not find compiled benchmark.sh."
                  fi
                  cd $ROOT_DIR
                else
                  echo "[+] IoT-Benchmark submodule is already compiled."
                fi
              else
                echo "[-] Warning: iot-benchmark submodule missing. Run: git submodule update --init"
              fi

              echo "======================================================="
              echo " Environment Ready!"
              echo "======================================================="
            '';
          };
        }
      );
    };
}
