import setuptools

setuptools.setup(
    name="aliveandwell-and-retainitwell",
    version="0.1",
    author="James Paige",
    author_email="james.robert.paige@gmail.com",
    description="Monitors a website and sends the metrics to Kafka",
    url="https://github.com/bob-the-hamster/aliveandwell-and-retainitwell",
    packages=["aliveandwell"],
    entry_points = {
        'console_scripts': ['aliveandwell=aliveandwell:aliveandwell_commandline_entrypoint'],
        },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        ],
    python_requires='>=3.5',
)
