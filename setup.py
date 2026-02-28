"""
CCTV Monitor — package configuration for pip / PyInstaller.
"""

from setuptools import setup

setup(
    name='cctv-monitor',
    version='1.2.0',
    description='Full-screen CCTV monitor with 4-channel RTSP preview and hardware acceleration',
    author='nickfu',
    py_modules=['cctv_monitor'],
    install_requires=[
        'opencv-python>=4.8.0',
        'Pillow>=10.0.0',
        'pytz>=2025.1',
    ],
    entry_points={
        'console_scripts': [
            'cctv-monitor=cctv_monitor:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Video :: Display',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.7',
)
