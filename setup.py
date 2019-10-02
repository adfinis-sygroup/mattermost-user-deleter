from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="mattermost-user-deleter",
    version="0.0.1",
    description="Delete Mattermost Users",
    url="https://github.com/adfinis-sygroup/mattermost-user-deleter",
    author="Adfinis SyGroup",
    license="AGPL-3.0",
    packages=["mattermost_user_deleter"],
    install_requires=requirements,
    zip_safe=False,
    entry_points={
        "console_scripts": ["mattermost-user-deleter=mattermost_user_deleter.app:main"]
    },
    data_files=[
        ('/usr/lib/systemd/system',[
            'config/mattermost-user-deleter.service',
            'config/mattermost-user-deleter.timer'
        ])
    ]
)
