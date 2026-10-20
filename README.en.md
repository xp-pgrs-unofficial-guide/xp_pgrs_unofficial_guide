# Unofficial Guide for XJTLU PhD Students

🌐 [中文版](README.md)

This guide shares practical experience about PhD research and life at XJTLU, supplementing the official induction. It was initiated by the XJTLU PGR Society and is maintained by volunteer editors.

- [Read online](https://xp-pgrs-unofficial-guide.github.io/xp_pgrs_unofficial_guide/): searchable articles with discussions and editing links. A maintainer must enable GitHub Pages for the first deployment.
- [Download the PDF](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/releases/latest): offline reading and versioned releases.
- [Contribute or report a correction](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide/issues/new/choose): complete a form with a GitHub account; no local Git or LaTeX installation is needed.

This repository contains the Chinese guide. There is also a separate [English guide project](https://github.com/xp-pgrs-unofficial-guide/xp_pgrs_unofficial_guide_EN).

## Content and contributions

The `.qmd` files (Quarto Markdown) under `book/content/` are the single source for ongoing content updates. They produce the website, a complete PDF, and plain Markdown for LLMs. Contribution blocks explicitly identify authors and later contributors; editorial commits do not replace the original author attribution.

Submit plain text through the contribution form for an editor to review, or use an article's edit link to propose a Markdown change directly on GitHub. Comments and submissions require a GitHub account. Content changes are reviewed by a person before publication. See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions and attribution examples.

The root LaTeX entry point, `chapters/`, and `author-folder/` remain as historical snapshots for checking the original text. Add new content to the Quarto source. The old LaTeX conversion and cloud deployment workflows are archived under `docs/legacy-workflows/` and no longer produce a separate content copy.

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

The build validates the source and writes to `book/_book/`: the PDF is `xp-pgrs-unofficial-guide.pdf`, plain Markdown is under `markdown/content/`, and `llms.txt` provides an index. Use `python3 scripts/build.py --check-only` to validate without rendering. LLMs can read the source or exported Markdown without a project-specific skill.

GitHub Actions validates branch pushes and pull requests. Pages deployment runs only for a push to `main` or a manual run from `main`. The existing `v*` tag workflow continues to publish PDF releases. See [maintainer setup](docs/maintainer-setup.md) for the initial Pages and comments configuration.
