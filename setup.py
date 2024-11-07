from setuptools import setup, find_packages

setup(
    name="starmate",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add dependencies here, e.g., 'numpy'
    ],
    entry_points={
        "console_scripts": [
            "starmate=starmate.main:main",  # Entry point for CLI
        ],
    },
    author="Your Name",
    description="A description of astroxs",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)
