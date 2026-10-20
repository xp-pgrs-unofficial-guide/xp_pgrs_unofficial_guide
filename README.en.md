# Unofficial Guide for XJTLU PhD Students

🌐 [中文版](README.md)

This guide shares practical experience about PhD research and life at XJTLU, supplementing the official induction. It was initiated by the XJTLU PGR Society and is maintained by volunteer editors.

- [Read online](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/): searchable articles with discussions, editing links, light/dark themes, and switching to the same article in either language.
- [Download the PDF](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/releases/latest): offline reading and versioned releases.
- [Contribute or report a correction](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new): submit text with a GitHub account; article-specific links prefill the page information. No local Git or LaTeX installation is needed.

This repository contains Chinese content and [English translations on the same site](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/en/). Matching articles share a discussion. English drafts are marked as awaiting human review. The separate [historical English project](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide_EN) is not the destination of this site’s language switch.

## Content and contributions

The Chinese home page is `book/index.qmd`, with `.qmd` files (Quarto Markdown) grouped into six topic directories under `book/content/`. English translations mirror these paths under `book/en/`. See the [article directory and file move guide](CONTRIBUTING.md#文章目录与文件移动) (in Chinese) for the directory map, new article locations, and compatibility with old URLs. Each language’s source produces its website, complete PDF, and plain Markdown for LLMs. Contribution blocks identify original authors and later contributors. Consecutive matching credits appear once on the website, with links to author pages; the navigation includes an author directory. Editorial commits do not replace original author attribution.

The website initially follows the system’s light/dark preference. A manual choice is retained in the browser and across language switches, and the discussion widget follows the current theme.

Use an article's contribution link to open an Issue draft with the page information prefilled, or choose its PR link to propose a Markdown change on GitHub. Readers without repository write access can follow GitHub's fork and pull request flow. Comments and submissions require a GitHub account. Content changes are reviewed by a person before publication. See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions and attribution examples.

Legacy LaTeX sources, author materials, and attachments are stored together in `archive/latex/`. Old workflows and the one-time migration tool are also under `archive/`. These materials support source checks; ongoing edits belong in the Quarto source. See the [archive guide](archive/README.md) (in Chinese).

See [project data flow](docs/data-flow.md) (in Chinese) for Mermaid diagrams of the build, publication, comments, and editorial contribution process.

## Repository layout

| Location | Purpose |
| --- | --- |
| `book/` | Chinese content, author registry, shared configuration, and publication assets; `authors/` contains author pages and `pdf/` contains current PDF styling. |
| `book/en/` | English translations mirroring the Chinese articles; project configuration is generated during the build. |
| `scripts/` | Current build entry point, `build.py`. |
| `tests/` | Checks for attribution, discussions, contribution links, and article paths. |
| `docs/` | Current data flow and maintenance documentation. |
| `.github/` | Active CI, release workflows, and contribution templates. |
| `archive/` | [Legacy LaTeX, attachments, workflows, and migration tooling](archive/README.md). |

## Preview and build locally

Install Python 3.12 and [Quarto 1.10.19](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19), then run:

```sh
python3 -m pip install -r requirements-build.txt
python3 scripts/build.py --html-only
quarto preview book
```

For the complete build, also install XeLaTeX, ctex, and the Fandol Chinese fonts supplied with TeX:

```sh
python3 scripts/build.py
```

One build command checks that translations match the Chinese sources and are current, then writes both languages: Chinese under `book/_book/`, and English in its `en/` subdirectory. Each contains `xp-pgrs-unofficial-guide.pdf`, `markdown/`, `llms.txt`, and a search index. The PDF cover, chapter headings, headers, and footers follow the historical ElegantBook style while using the current Quarto content. Use `python3 scripts/build.py --check-only` to validate without rendering. LLMs can read the source or exported Markdown without a project-specific skill.

After a build, use `quarto preview book/en` to preview English. Do not edit the generated `book/en/_quarto.yml` manually.

GitHub Actions validates branch pushes and pull requests. Pages deploys for a push or manual run from `main`, or a manual preview run from `codex/quarto-guide`. Ordinary feature-branch pushes do not deploy. The existing `v*` tag workflow continues to publish PDF releases. See [maintainer setup](docs/maintainer-setup.md) for Pages, comments, and branch preview configuration.
