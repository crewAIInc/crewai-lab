"""Reference solution for module 01."""

from lab_utils.agents import research_company


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "company",
        nargs="?",
        default="CrewAI",
        help="Any public company to research (defaults to CrewAI).",
    )
    args = parser.parse_args()
    brief = research_company(args.company)
    print(brief.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
