import setuptools

setuptools.setup(
    name="metaedit",
    version="0.0.1",
    author="Liam Emmart",
    author_email="l.emmart@outlook.com",
    description="Image and metadata attribute viewer and editor.",
    long_description_content_type="text/markdown",
    url="https://github.com/Lemmart/metaedit",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: GNU Affero General Public License v3.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
