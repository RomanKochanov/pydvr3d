from setuptools import find_packages, setup

setup(
    name="pydvr3d",
    version="0.1",
    author="Roman Kochanov",
    author_email="",
    description="Python wrapper for DRV3D program suite",
    #url="",
    python_requires=">=3.5",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL-3",
        "Operating System :: OS Independent",
    ],
    #install_requires=[],
    entry_points = {
        'console_scripts': ['pydvr3d=pydvr3d.command_line:main']
    }
)
