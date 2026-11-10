from pathlib import Path
import re


def test_dev_compose_dockerfile_resolves_inside_build_context():
    compose = Path("infra/docker-compose.yml").read_text()
    try:
        import yaml
    except ImportError:
        context = re.search(r"(?m)^\s+context:\s*(\S+)\s*$", compose).group(1)
        dockerfile = re.search(r"(?m)^\s+dockerfile:\s*(\S+)\s*$", compose).group(1)
    else:
        service = yaml.safe_load(compose)["services"]["api"]["build"]
        context, dockerfile = service["context"], service["dockerfile"]

    build_context = (Path("infra") / context).resolve()
    assert (build_context / dockerfile).is_file()


def test_ci_apt_cache_matches_guarded_script_directory():
    workflow = Path(".github/workflows/tests.yml").read_text()
    cache_block = re.search(
        r"(?ms)uses:\s*actions/cache@v4\s*\n\s*with:\s*\n\s*path:\s*(\S+)", workflow
    )
    script_dirs = set(re.findall(r'\$HOME/(\.cache/[^" ]+)', workflow))

    assert cache_block is not None
    assert cache_block.group(1).replace("~/", "") in script_dirs
    assert any(path.startswith(".cache/apt-runtime") for path in script_dirs)
