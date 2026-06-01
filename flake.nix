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

          injectPrintCss = pkgs.writeText "inject-print-css.py"
            (builtins.readFile ./scripts/inject-print-css.py);

          fmtApp = pkgs.writeShellApplication {
            name = "fmt-thesis";
            runtimeInputs = with pkgs; [ git bibtex-tidy tex-fmt findutils ];
            text = builtins.readFile ./scripts/fmt-thesis.sh;
          };

          thesisApp = pkgs.writeShellApplication {
            name = "build-thesis";
            runtimeInputs = [ texlive pkgs.git ];
            text = builtins.readFile ./scripts/build-thesis.sh;
          };

          slidesPdfApp = pkgs.writeShellApplication {
            name = "slides-pdf";
            runtimeInputs = with pkgs; [ git python3 chromium ];
            text = ''
              export INJECT_CSS_SCRIPT="${injectPrintCss}"
            '' + builtins.readFile ./scripts/slides-pdf.sh;
          };
        in
        {
          thesis     = { type = "app"; program = "${thesisApp}/bin/build-thesis"; };
          fmt        = { type = "app"; program = "${fmtApp}/bin/fmt-thesis"; };
          slides-pdf = { type = "app"; program = "${slidesPdfApp}/bin/slides-pdf"; };
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
              (python3.withPackages (ps: with ps; [ matplotlib numpy pandas ]))
              gnused
              findutils
              git
              bibtex-tidy
              tex-fmt
            ];
            shellHook = builtins.readFile ./scripts/dev-shell-hook.sh;
          };
        }
      );
    };
}
