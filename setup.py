from pathlib import Path

from setuptools import find_packages, setup


project_root = Path(__file__).parent

requirements = [
    line.strip()
    for line in (project_root / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]


setup(
    name="pink-annotation-schema",
    version="0.2",
    packages=find_packages(where="src") + ["validation"],
    package_dir={"": "src", "validation": "validation"},
    entry_points={
        "console_scripts": ["generate-graph=pink.generate_graph:main"]
    },
    install_requires=requirements,
)
