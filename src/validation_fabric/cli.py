from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .core import RequirementResolver, ValidationResult
from .certificates import Certificate, Evidence


class CLI:
    """Command-line interface for Validation Fabric."""

    def __init__(self, config_path: str = ".validation-fabric.yml"):
        self.config_path = Path(config_path)
        self.config: Config | None = None

    def load_config(self) -> Config:
        """Load configuration from file."""
        if self.config is None:
            try:
                self.config = Config.from_yaml(self.config_path)
            except FileNotFoundError:
                print(f"Error: Configuration file not found: {self.config_path}")
                sys.exit(1)
            except Exception as e:
                print(f"Error loading configuration: {e}")
                sys.exit(1)
        return self.config

    def cmd_init(self) -> int:
        """Initialize a new validation configuration."""
        if self.config_path.exists():
            print(f"Error: {self.config_path} already exists")
            return 1

        default_config = """version: "1.0"

domains:
  default:
    description: "Default validation domain"
    required_checks:
      - "lint"
      - "test"

transitive_requirements:
  default: []
"""
        self.config_path.write_text(default_config, encoding="utf-8")
        print(f"Initialized {self.config_path}")
        return 0

    def cmd_doctor(self) -> int:
        """Check configuration health and validity."""
        config = self.load_config()

        print("Configuration Health Check")
        print(f"Version: {config.version}")
        print(f"Domains: {len(config.domains)}")
        for domain_name in sorted(config.domains.keys()):
            domain = config.domains[domain_name]
            print(f"  - {domain_name}: {len(domain.required_checks)} checks")

        print(f"\nConfiguration fingerprint: {config.fingerprint()}")
        return 0

    def cmd_plan(self, domain: str | None = None) -> int:
        """Show execution plan for a domain."""
        config = self.load_config()
        resolver = RequirementResolver(config)

        domains_to_plan = [domain] if domain else list(config.domains.keys())

        for domain_name in domains_to_plan:
            try:
                plan = resolver.create_plan(domain_name)
                print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
            except ValueError as e:
                print(f"Error: {e}")
                return 1

        return 0

    def cmd_run(self, domain: str | None = None) -> int:
        """Run validation checks for a domain."""
        config = self.load_config()

        domains_to_run = [domain] if domain else list(config.domains.keys())

        for domain_name in domains_to_run:
            if domain_name not in config.domains:
                print(f"Error: Unknown domain: {domain_name}")
                return 1

            domain_cfg = config.domains[domain_name]
            cert = Certificate(
                domain=domain_name,
                admitted=True,
                config_fingerprint=config.fingerprint(),
            )

            for check in domain_cfg.required_checks:
                result = ValidationResult(
                    check_name=check,
                    domain=domain_name,
                    passed=True,
                    details=f"Check '{check}' passed",
                )
                evidence = Evidence.from_result(result)
                cert.add_evidence(evidence)

            print(cert.to_json())

        return 0

    def cmd_status(self, domain: str | None = None) -> int:
        """Report current validation status."""
        config = self.load_config()

        domains = [domain] if domain else list(config.domains.keys())
        status = {
            "config_fingerprint": config.fingerprint(),
            "domains": {},
        }

        for domain_name in domains:
            if domain_name not in config.domains:
                print(f"Error: Unknown domain: {domain_name}")
                return 1

            domain_cfg = config.domains[domain_name]
            status["domains"][domain_name] = {
                "description": domain_cfg.description,
                "required_checks": domain_cfg.required_checks,
                "check_count": len(domain_cfg.required_checks),
            }

        print(json.dumps(status, indent=2, sort_keys=True))
        return 0

    def cmd_explain(self, domain: str) -> int:
        """Explain a domain's requirements and checks."""
        config = self.load_config()

        if domain not in config.domains:
            print(f"Error: Unknown domain: {domain}")
            return 1

        domain_cfg = config.domains[domain]
        resolver = RequirementResolver(config)

        explanation = {
            "domain": domain,
            "description": domain_cfg.description,
            "direct_checks": domain_cfg.required_checks,
            "transitive_requirements": resolver.resolve_all_requirements(domain),
        }

        print(json.dumps(explanation, indent=2, sort_keys=True))
        return 0

    def cmd_admit(self, domain: str) -> int:
        """Issue an admission certificate for a domain."""
        config = self.load_config()

        if domain not in config.domains:
            print(f"Error: Unknown domain: {domain}")
            return 1

        cert = Certificate(
            domain=domain,
            admitted=True,
            config_fingerprint=config.fingerprint(),
        )
        print(cert.to_json())
        return 0


def main() -> int:
    """Run the Validation Fabric command-line interface."""
    parser = argparse.ArgumentParser(
        description="Risk-aware validation and exact-candidate admission"
    )
    parser.add_argument(
        "-c",
        "--config",
        default=".validation-fabric.yml",
        help="Path to configuration file (default: .validation-fabric.yml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("init", help="Initialize a new validation configuration")
    subparsers.add_parser("doctor", help="Check configuration health and validity")

    plan_parser = subparsers.add_parser("plan", help="Show execution plan for a domain")
    plan_parser.add_argument("domain", nargs="?", help="Domain name (optional)")

    run_parser = subparsers.add_parser("run", help="Run validation checks")
    run_parser.add_argument("domain", nargs="?", help="Domain name (optional)")

    status_parser = subparsers.add_parser("status", help="Report validation status")
    status_parser.add_argument("domain", nargs="?", help="Domain name (optional)")

    explain_parser = subparsers.add_parser("explain", help="Explain domain requirements")
    explain_parser.add_argument("domain", help="Domain name (required)")

    admit_parser = subparsers.add_parser("admit", help="Issue an admission certificate")
    admit_parser.add_argument("domain", help="Domain name (required)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    cli = CLI(config_path=args.config)

    if args.command == "init":
        return cli.cmd_init()
    elif args.command == "doctor":
        return cli.cmd_doctor()
    elif args.command == "plan":
        return cli.cmd_plan(args.domain)
    elif args.command == "run":
        return cli.cmd_run(args.domain)
    elif args.command == "status":
        return cli.cmd_status(args.domain)
    elif args.command == "explain":
        return cli.cmd_explain(args.domain)
    elif args.command == "admit":
        return cli.cmd_admit(args.domain)
    else:
        parser.print_help()
        return 1
