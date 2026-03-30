from setuptools import find_packages, setup

with open("README.md") as fp:
    long_description = fp.read()

setup(
    name="lmjm",
    use_scm_version={
        "relative_to": __file__,
        "local_scheme": "node-and-timestamp",
        "fallback_version": "0.0.1"
    },
    setup_requires=['setuptools_scm'],

    description="Interface to interact with Skill Builder apis",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Lucas Machado",
    author_email="lucasam@gmail.com",

    include_package_data=True,
    packages=find_packages(where="src"),
    package_dir={"": "src"},

    python_requires=">=3.11",

    classifiers=[
        "Programming Language :: Python :: 3.11"
    ],
)
