from setuptools import find_packages, setup

setup(
    packages=find_packages(include=["guard_agent", "guard_agent.*"]),
    include_package_data=True,
    package_data={
        "guard_agent": ["py.typed"],
    },
)
