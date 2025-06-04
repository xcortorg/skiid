from setuptools import setup, find_packages


# Function to load the requirements from the requirements.txt file
def parse_requirements(filename):
    with open(filename, "r") as file:
        return file.readlines()


setup(
    name="DataProcessing",
    version="1.0.0",  # Update version as needed
    description="A package for scraping web services and processing data.",
    author="cop-discord",  # Replace with your name
    author_email="cop@catgir.ls",  # Replace with your email
    url="https://github.com/cop-discord/DataProcessing",  # Replace with your repository URL
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],  # Automatically read from requirements.txt
    python_requires=">=3.6",  # Specify minimum Python version
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Update with your license
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Web Scraping",
    ],
    keywords="data processing web scraping services lxml beautifulsoup requests",
    entry_points={
        "console_scripts": [
            "dataprocessor=DataProcessing.cli:main",  # Replace with actual entry point if needed
        ],
    },
)
