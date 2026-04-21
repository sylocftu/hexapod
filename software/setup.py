from setuptools import setup, find_packages

setup(
    name="hexapod-core",
    version="0.1.0",
    description="Hexapod robot core library — kinematics, gait engine, hardware drivers, and API",
    author="STEM Hexapod Project",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.110.0",
        "uvicorn[standard]==0.29.0",
        "smbus2==0.4.3",
        "numpy==1.26.4",
        "scipy==1.13.0",
        "pydantic==2.6.4",
        "websockets==12.0",
        "python-multipart==0.0.22",
        "opencv-python-headless==4.9.0.80",
    ],
    extras_require={
        "dev": [
            "pytest==8.1.1",
            "pytest-asyncio==0.23.6",
            "httpx==0.27.0",
            "flake8",
            "black",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Robotics",
    ],
)
